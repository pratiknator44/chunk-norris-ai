"""Schema parsing and natural-language inference endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.llm import infer_shape_from_nl
from app.core.schema import shape_tree_to_json_schema
from app.core.shape import detect_mode, parse_shape

router = APIRouter(prefix="/schemas", tags=["schemas"])


class ParseSchemaRequest(BaseModel):
    text: str


class ParseErrorDetail(BaseModel):
    line: int
    col: int
    message: str


class ParseSchemaResponse(BaseModel):
    ok: bool
    mode: str  # "shape" | "natural_language"
    shape_tree: dict[str, Any] | None = None
    json_schema: dict[str, Any] | None = None
    errors: list[ParseErrorDetail] = []
    reason: str | None = None


class InferShapeRequest(BaseModel):
    request: str


class InferShapeResponse(BaseModel):
    shape_text: str
    shape_tree: dict[str, Any]
    json_schema: dict[str, Any]


@router.post("/parse", response_model=ParseSchemaResponse)
async def parse_schema_endpoint(payload: ParseSchemaRequest) -> ParseSchemaResponse:
    mode, info = detect_mode(payload.text)

    if mode == "shape":
        if info.get("ok"):
            try:
                tree = parse_shape(payload.text.strip())
                json_schema = shape_tree_to_json_schema(tree)
                return ParseSchemaResponse(
                    ok=True,
                    mode="shape",
                    shape_tree=tree.to_dict(),
                    json_schema=json_schema,
                )
            except Exception as e:
                return ParseSchemaResponse(
                    ok=False,
                    mode="shape",
                    errors=[ParseErrorDetail(line=1, col=1, message=str(e))],
                )
        else:
            errors_raw = info.get("errors", [])
            errors = [
                ParseErrorDetail(line=e["line"], col=e["col"], message=e["message"])
                for e in errors_raw
            ]
            return ParseSchemaResponse(
                ok=False,
                mode="shape",
                errors=errors,
            )

    return ParseSchemaResponse(
        ok=False,
        mode="natural_language",
        reason="plain_english",
    )


@router.post("/infer", response_model=InferShapeResponse)
async def infer_shape_endpoint(payload: InferShapeRequest) -> InferShapeResponse:
    if not payload.request.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request text cannot be empty.",
        )

    try:
        tree, shape_text = await infer_shape_from_nl(payload.request)
        json_schema = shape_tree_to_json_schema(tree)
        return InferShapeResponse(
            shape_text=shape_text,
            shape_tree=tree.to_dict(),
            json_schema=json_schema,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to infer shape from request: {e}",
        ) from e
