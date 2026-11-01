
import json
import re
import time
import hashlib
import traceback

from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.progress import PageCompletedProgress

from openai import OpenAI, BadRequestError
from pydantic import create_model, Field, ValidationError, ConfigDict


# ============================================================
# CONFIGURATION
# ============================================================

PDF_PATH = Path("resume.pdf")

OUTPUT_PATH = Path("result.json")

# Cached Docling output. Avoids reparsing on subsequent runs.
TEXT_CACHE_PATH = Path("parsed_document.md")

# Progress checkpoint for LLM extraction.
CHECKPOINT_PATH = Path("extraction_checkpoint.json")

# LM Studio configuration.
LM_STUDIO_URL = "http://192.168.0.5:1234/v1"
API_KEY = "lm-studio"

# Automatically select first loaded model.
MODEL_ID = None

# Chunk configuration.
MAX_CHARS_PER_CHUNK = 8000

# LLM configuration.
MAX_OUTPUT_TOKENS = 4096
TEMPERATURE = 0

# Set False to force PDF reparsing.
USE_TEXT_CACHE = True

START_TIME = time.time()


# ============================================================
# YOUR REQUIRED OUTPUT SCHEMA
# ============================================================

SCHEMA = {
    "characterNames": ["string"],
    "countriesMentioned": ["string"]
}


# ============================================================
# 1. GENERATE JSON SCHEMA
# ============================================================

def generate_json_schema(fields):

    properties = {}

    for name, field_type in fields.items():

        if field_type == "string":

            properties[name] = {
                "type": ["string", "null"]
            }

        elif field_type == "number":

            properties[name] = {
                "type": ["number", "null"]
            }

        elif field_type == ["string"]:

            properties[name] = {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }

        else:
            raise ValueError(
                f"Unsupported field type: {name} = {field_type}"
            )

    return {
        "type": "object",
        "properties": properties,
        "required": list(fields.keys()),
        "additionalProperties": False
    }


# ============================================================
# 2. GENERATE PYDANTIC VALIDATION MODEL
# ============================================================

def generate_pydantic_model(fields):

    model_fields = {}

    for name, field_type in fields.items():

        if field_type == "string":

            model_fields[name] = (
                str | None,
                Field(default=None)
            )

        elif field_type == "number":

            model_fields[name] = (
                float | None,
                Field(default=None)
            )

        elif field_type == ["string"]:

            model_fields[name] = (
                list[str],
                Field(default_factory=list)
            )

        else:
            raise ValueError(
                f"Unsupported field type: {name}"
            )

    return create_model(
        "ExtractedDocument",
        __config__=ConfigDict(extra="forbid"),
        **model_fields
    )


# ============================================================
# 3. CONNECT TO LM STUDIO
# ============================================================

def connect_lm_studio():

    print("\n[LM STUDIO] Connecting...")

    client = OpenAI(
        base_url=LM_STUDIO_URL,
        api_key=API_KEY,
        timeout=600
    )

    models = client.models.list().data

    if not models:

        raise RuntimeError(
            "No models loaded in LM Studio."
        )

    print("\nAvailable models:")

    for model in models:
        print(f" - {model.id}")

    selected_model = MODEL_ID or models[0].id

    print(f"\nSelected model: {selected_model}")

    return client, selected_model


# ============================================================
# 4. DOCLING PROGRESS CALLBACK
# ============================================================

def on_progress(event):

    if isinstance(event, PageCompletedProgress):

        completed = event.completed_pages
        total = event.total_pages

        percentage = (
            completed / total * 100
            if total else 0
        )

        elapsed = time.time() - START_TIME

        print(
            f"\r[PDF PARSING] "
            f"{completed}/{total} pages "
            f"({percentage:.1f}%) | "
            f"{elapsed:.1f}s",
            end="",
            flush=True
        )


# ============================================================
# 5. PARSE PDF USING DOCLING
# ============================================================

def parse_pdf(pdf_path):

    # Reuse previously parsed Markdown.
    if USE_TEXT_CACHE and TEXT_CACHE_PATH.exists():

        print("\n[CACHE] Loading previously parsed document...")

        document_text = TEXT_CACHE_PATH.read_text(
            encoding="utf-8"
        )

        print(
            f"[CACHE] Loaded {len(document_text):,} characters."
        )

        return document_text

    print("\n[1/5] Initializing Docling...")

    converter = DocumentConverter()

    print("[2/5] Parsing PDF...")

    result = converter.convert(
        str(pdf_path),
        progress_callback=on_progress
    )

    print("\nPDF parsing completed.")

    document_text = result.document.export_to_markdown()

    print(
        f"Extracted text: {len(document_text):,} characters"
    )

    # Cache Markdown for future runs.
    print("\n[CACHE] Saving parsed document...")

    TEXT_CACHE_PATH.write_text(
        document_text,
        encoding="utf-8"
    )

    print(f"[CACHE] Saved: {TEXT_CACHE_PATH}")

    return document_text


# ============================================================
# 6. SPLIT DOCUMENT INTO CHUNKS
# ============================================================

def split_document(text, max_chars=MAX_CHARS_PER_CHUNK):

    print("\n[CHUNKING] Splitting document...")

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    chunks = []

    current_chunk = ""

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Handle exceptionally long paragraphs.
        while len(paragraph) > max_chars:

            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            split_at = paragraph.rfind(
                " ",
                0,
                max_chars
            )

            if split_at <= 0:
                split_at = max_chars

            chunks.append(paragraph[:split_at].strip())

            paragraph = paragraph[split_at:].strip()

        separator = "\n\n" if current_chunk else ""

        if (
            len(current_chunk)
            + len(separator)
            + len(paragraph)
            > max_chars
        ):

            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = paragraph

        else:

            current_chunk += separator + paragraph

    if current_chunk:
        chunks.append(current_chunk)

    print(f"[CHUNKING] Created {len(chunks)} chunks.")

    return chunks


# ============================================================
# 7. CHECKPOINT MANAGEMENT
# ============================================================

def get_source_hash(document_text):

    combined = (
        document_text
        + json.dumps(SCHEMA, sort_keys=True)
    )

    return hashlib.sha256(
        combined.encode("utf-8")
    ).hexdigest()


def load_checkpoint(source_hash, total_chunks):

    if CHECKPOINT_PATH.exists():

        try:

            with open(
                CHECKPOINT_PATH,
                "r",
                encoding="utf-8"
            ) as file:

                checkpoint = json.load(file)

            if (
                checkpoint.get("source_hash") == source_hash
                and checkpoint.get("total_chunks") == total_chunks
            ):

                print(
                    f"\n[CHECKPOINT] Resuming extraction."
                )

                return checkpoint

            print(
                "\n[CHECKPOINT] Document or schema changed. "
                "Starting fresh."
            )

        except Exception:

            print(
                "\n[CHECKPOINT] Invalid checkpoint. "
                "Starting fresh."
            )

    return {
        "source_hash": source_hash,
        "total_chunks": total_chunks,
        "completed": {}
    }


def save_checkpoint(checkpoint):

    with open(
        CHECKPOINT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            checkpoint,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# 8. EXTRACT INFORMATION FROM ONE CHUNK
# ============================================================

def extract_chunk(client, model, chunk, chunk_number, total_chunks):

    validation_model = generate_pydantic_model(SCHEMA)

    json_schema = generate_json_schema(SCHEMA)

    schema_description = json.dumps(
        SCHEMA,
        indent=2
    )

    system_prompt = """
You are a precise document information extraction engine.

Extract ONLY information explicitly supported by the
provided document text.

STRICT RULES:

1. Return only the requested JSON fields.
2. Never invent information.
3. Do not add explanations or additional properties.
4. For missing strings or numbers, return null.
5. For missing arrays, return [].
6. Preserve names exactly as written.
7. Include all relevant matches found in this chunk.
8. Do not omit relevant entities simply because they
   appear multiple times.
9. Distinguish actual character names from ordinary
   words, authors, publishers and organizations.
10. Distinguish countries from cities and regions.

The supplied JSON Schema defines the exact output format.
"""

    user_prompt = f"""
Extract the requested information from this document chunk.

REQUESTED FIELDS:
{schema_description}

CHUNK:
{chunk}

Return only the requested JSON object.
"""

    print(
        f"\n[LLM] Processing chunk "
        f"{chunk_number}/{total_chunks} "
        f"({len(chunk):,} characters)"
    )

    try:

        response = client.chat.completions.create(

            model=model,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],

            # LM Studio-compatible structured output.
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "document_extraction",
                    "strict": True,
                    "schema": json_schema
                }
            },

            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS
        )

    except BadRequestError as error:

        print("\n[LM STUDIO] BAD REQUEST")

        if error.response is not None:
            print(error.response.text)
        else:
            print(str(error))

        raise

    raw_output = response.choices[0].message.content

    if not raw_output:

        raise RuntimeError(
            f"Empty response for chunk {chunk_number}"
        )

    if response.choices[0].finish_reason == "length":

        raise RuntimeError(
            f"Output token limit reached in chunk {chunk_number}. "
            "Increase MAX_OUTPUT_TOKENS or reduce chunk size."
        )

    extracted = json.loads(raw_output)

    validated = validation_model.model_validate(extracted)

    return validated.model_dump()


# ============================================================
# 9. PROCESS ALL CHUNKS
# ============================================================

def process_chunks(client, model, chunks, document_text):

    source_hash = get_source_hash(document_text)

    checkpoint = load_checkpoint(
        source_hash,
        len(chunks)
    )

    completed = checkpoint["completed"]

    for index, chunk in enumerate(chunks):

        chunk_key = str(index)

        # Skip already completed chunks.
        if chunk_key in completed:

            print(
                f"\n[SKIP] Chunk {index + 1}/{len(chunks)} "
                "already completed."
            )

            continue

        result = extract_chunk(
            client,
            model,
            chunk,
            index + 1,
            len(chunks)
        )

        # Save each successful chunk immediately.
        completed[chunk_key] = result

        save_checkpoint(checkpoint)

        print(
            f"[SAVED] Chunk {index + 1}/{len(chunks)} completed."
        )

    print("\n[LLM] All chunks processed.")

    return list(completed.values())


# ============================================================
# 10. MERGE AND DEDUPLICATE RESULTS
# ============================================================

def merge_results(results):

    print("\n[MERGE] Combining extracted information...")

    merged = {}

    for field_name, field_type in SCHEMA.items():

        if field_type == ["string"]:

            combined = []

            seen = set()

            for result in results:

                values = result.get(field_name, [])

                for value in values:

                    value = str(value).strip()

                    if not value:
                        continue

                    normalized = value.casefold()

                    if normalized not in seen:

                        seen.add(normalized)
                        combined.append(value)

            merged[field_name] = combined

        else:

            # For scalar fields, keep the first
            # non-null value found across chunks.
            value = None

            for result in results:

                candidate = result.get(field_name)

                if candidate is not None and candidate != "":

                    value = candidate
                    break

            merged[field_name] = value

    return merged


# ============================================================
# 11. SAVE FINAL JSON
# ============================================================

def save_output(data):

    print("\n[OUTPUT] Saving final JSON...")

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"[OUTPUT] Saved: {OUTPUT_PATH.resolve()}")


# ============================================================
# 12. MAIN
# ============================================================

def main():

    start = time.time()

    print("=" * 65)
    print("       PDF TO CUSTOM JSON EXTRACTION ENGINE")
    print("=" * 65)

    if not PDF_PATH.exists():

        print(
            f"\nERROR: PDF not found: {PDF_PATH.resolve()}"
        )

        return

    try:

        # Connect to LM Studio.
        client, model = connect_lm_studio()

        # Parse PDF or reuse cached Markdown.
        document_text = parse_pdf(PDF_PATH)

        if not document_text.strip():

            raise RuntimeError(
                "No text was extracted from the PDF."
            )

        # Split document.
        chunks = split_document(document_text)

        if not chunks:

            raise RuntimeError(
                "No chunks were created."
            )

        # Process chunks.
        results = process_chunks(
            client,
            model,
            chunks,
            document_text
        )

        # Merge results.
        final_result = merge_results(results)

        # Save final JSON.
        save_output(final_result)

        # Final summary.
        elapsed = time.time() - start

        print("\n" + "=" * 65)
        print("FINAL EXTRACTION RESULT")
        print("=" * 65)

        print(
            json.dumps(
                final_result,
                indent=2,
                ensure_ascii=False
            )
        )

        print("\n" + "=" * 65)
        print(f"Chunks processed : {len(results)}")
        print(f"Total time       : {elapsed:.2f}s")
        print(f"Output           : {OUTPUT_PATH}")
        print("STATUS           : SUCCESS")
        print("=" * 65)

    except ValidationError as error:

        print("\nJSON VALIDATION ERROR:")
        print(error)

    except KeyboardInterrupt:

        print(
            "\n\nInterrupted. Completed chunks are saved."
        )

    except Exception as error:

        print(f"\nERROR: {error}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
