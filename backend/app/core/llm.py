"""LM Studio / OpenAI client integration for DocExtract.

Provides:
- Concurrency limiting via asyncio.Semaphore (default 1 for local GPU).
- Exponential backoff retries on network/transient failures.
- Token length limit detection (TokenLimitExceededError).
- Model discovery and automatic selection.
- Natural language to shape language inference.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, cast

from openai import AsyncOpenAI, BadRequestError

from app.config import settings
from app.core.prompts import (
    build_nl_shape_prompts,
    build_nl_shape_retry_prompts,
)
from app.core.shape import ParseError, ShapeTree, parse_shape

logger = logging.getLogger(__name__)

# Global semaphore initialized lazily
_semaphore: asyncio.Semaphore | None = None


def get_llm_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.llm_concurrency)
    return _semaphore


class TokenLimitExceededError(Exception):
    """Raised when LLM hits max output tokens (finish_reason == 'length')."""

    def __init__(self, message: str, chunk_text: str):
        super().__init__(message)
        self.chunk_text = chunk_text


def get_async_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.lm_studio_url,
        api_key=settings.lm_studio_api_key,
        timeout=settings.llm_timeout_s,
    )


async def get_active_model_id(client: AsyncOpenAI | None = None) -> str:
    """Returns the configured model id, or the first active model reported by LM Studio."""
    if settings.llm_model.strip():
        return settings.llm_model.strip()

    cl = client or get_async_openai_client()
    try:
        model_list = await cl.models.list()
        if not model_list.data:
            raise RuntimeError("No models loaded in LM Studio.")
        return model_list.data[0].id
    except Exception as e:
        logger.warning(f"Could not fetch models from LM Studio: {e}")
        return "local-model"


async def extract_chunk_json(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    chunk_text: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Sends extraction request to LM Studio with strict structured output.

    Handles retries and flags token length overflows.
    """
    semaphore = get_llm_semaphore()

    for attempt in range(1, max_retries + 1):
        try:
            async with semaphore:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "document_extraction",
                            "strict": True,
                            "schema": json_schema,
                        },
                    },
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_output_tokens,
                )

            choice = response.choices[0]

            if choice.finish_reason == "length":
                raise TokenLimitExceededError(
                    "LLM hit max_tokens limit for chunk",
                    chunk_text=chunk_text,
                )

            content = choice.message.content
            if not content:
                raise RuntimeError("LLM returned empty response")

            parsed: Any = json.loads(content)
            return cast(dict[str, Any], parsed)

        except TokenLimitExceededError:
            raise  # Do not retry as-is; caller must halve chunk size

        except BadRequestError as e:
            logger.error(f"LM Studio bad request error on attempt {attempt}: {e}")
            raise

        except Exception as e:
            if attempt == max_retries:
                logger.error(f"LLM extraction failed after {max_retries} attempts: {e}")
                raise
            delay = 2**attempt
            logger.warning(
                "LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt,
                max_retries,
                e,
                delay,
            )
            await asyncio.sleep(delay)

    raise RuntimeError("Extraction failed")


def _clean_inferred_shape(raw_text: str) -> str:
    """Strips markdown code fences and extraneous text from LLM shape output."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:typescript|ts|json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        return match.group(1).strip()
    return cleaned


async def infer_shape_from_nl(
    user_request: str,
    client: AsyncOpenAI | None = None,
    model: str | None = None,
) -> tuple[ShapeTree, str]:
    """Infers a ShapeTree from a natural-language description.

    Retries once with parse errors if the initial output has syntax issues.
    Returns:
        tuple[ShapeTree, str]: (parsed_tree, raw_shape_text)
    """
    cl = client or get_async_openai_client()
    mdl = model or await get_active_model_id(cl)
    semaphore = get_llm_semaphore()

    sys_prompt, usr_prompt = build_nl_shape_prompts(user_request)

    async with semaphore:
        resp = await cl.chat.completions.create(
            model=mdl,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": usr_prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )

    raw_shape = _clean_inferred_shape(resp.choices[0].message.content or "")

    try:
        tree = parse_shape(raw_shape)
        return tree, raw_shape
    except ParseError as err:
        logger.warning(f"Inferred shape failed initial parse: {err}. Retrying with feedback...")
        retry_sys, retry_usr = build_nl_shape_retry_prompts(user_request, raw_shape, str(err))
        async with semaphore:
            retry_resp = await cl.chat.completions.create(
                model=mdl,
                messages=[
                    {"role": "system", "content": retry_sys},
                    {"role": "user", "content": retry_usr},
                ],
                temperature=0.0,
                max_tokens=1500,
            )

        fixed_shape = _clean_inferred_shape(retry_resp.choices[0].message.content or "")
        tree = parse_shape(fixed_shape)
        return tree, fixed_shape
