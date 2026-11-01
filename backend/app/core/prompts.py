"""Prompt templates and builders for DocExtract.

Generates:
1. Extraction system & user prompts dynamically driven by the ShapeTree / JSON Schema.
2. Natural-language to shape language inference prompts (with retry on parse failure).
"""

from __future__ import annotations

from typing import Any

from app.core.shape import (
    ArrayNode,
    EnumNode,
    ObjectNode,
    ScalarNode,
    ShapeNode,
    ShapeTree,
)


def _collect_field_descriptions(node: ShapeNode, prefix: str = "") -> list[str]:
    """Recursively walks a ShapeNode and formats field descriptions and types for prompt context."""
    lines: list[str] = []

    if isinstance(node, ObjectNode):
        for key, child in node.fields.items():
            field_path = f"{prefix}.{key}" if prefix else key
            desc = f" ({child.description})" if child.description else ""
            if isinstance(child, ScalarNode):
                lines.append(f"- `{field_path}`: {child.kind}{desc}")
            elif isinstance(child, EnumNode):
                vals = ", ".join(f'"{v}"' for v in child.values)
                lines.append(f"- `{field_path}`: enum [{vals}]{desc}")
            elif isinstance(child, ArrayNode):
                if isinstance(child.element_type, ObjectNode):
                    lines.append(f"- `{field_path}`: list of objects{desc}")
                    lines.extend(_collect_field_descriptions(child.element_type, f"{field_path}[]"))
                elif isinstance(child.element_type, ScalarNode):
                    lines.append(f"- `{field_path}`: list of {child.element_type.kind}{desc}")
                elif isinstance(child.element_type, EnumNode):
                    vals = ", ".join(f'"{v}"' for v in child.element_type.values)
                    lines.append(f"- `{field_path}`: list of enum [{vals}]{desc}")
            elif isinstance(child, ObjectNode):
                lines.append(f"- `{field_path}`: object{desc}")
                lines.extend(_collect_field_descriptions(child, field_path))

    elif isinstance(node, ArrayNode) and isinstance(node.element_type, ObjectNode):
        lines.append("- List items:")
        lines.extend(_collect_field_descriptions(node.element_type, "item"))

    return lines


def build_extraction_prompts(
    tree: ShapeTree,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    json_schema: dict[str, Any],
) -> tuple[str, str]:
    """Builds (system_prompt, user_prompt) for chunk extraction."""
    system_prompt = """You are a precise document information extraction engine.

Extract ONLY information explicitly supported by the provided document chunk.

STRICT RULES:
1. Return ONLY the requested JSON structure adhering strictly to the JSON Schema.
2. Never invent or hallucinate information not present in the text.
3. For missing or unfound strings/numbers/dates, return null.
4. For missing or unfound arrays/lists, return [].
5. Format dates as ISO 8601 (YYYY-MM-DD) if date format is requested.
6. Preserve names, identifiers, and numbers exactly as written in the text.
7. Include all relevant matches found in this chunk.
8. Do not add explanations or wrapper text outside the JSON object."""

    field_lines = _collect_field_descriptions(tree.root)
    fields_summary = "\n".join(field_lines) if field_lines else "Extract according to schema."

    user_prompt = f"""Extract information from Chunk {chunk_index}/{total_chunks}.

REQUESTED FIELDS:
{fields_summary}

DOCUMENT CHUNK:
{chunk_text}

Return only the valid JSON object conforming to the schema."""

    return system_prompt, user_prompt


# ----------------------------------------------------------------------
# Natural-language to Shape Language Inference
# ----------------------------------------------------------------------

NL_SHAPE_SYSTEM_PROMPT = """You are an expert data architect for an information extraction system.
Convert the user's natural language extraction request into a clean DocExtract shape definition.

SHAPE LANGUAGE SPECIFICATION:
- Root must be an object `{ ... }` or a top-level array `[ { ... } ]`.
- Primitive types: `string`, `number`, `integer`, `boolean`, `date`.
- Enums: string literal unions like status: "open" | "closed" | "pending".
- Optional fields: `T?` (e.g. `age: number?`).
- Lists: `[ T ]` or `T[]` (e.g. `skills: [string]`, `employees: [ { name: string } ]`).
- Comments: `// description` after field definition to provide context for extraction.
- Valid identifier names: `^[A-Za-z_][A-Za-z0-9_]*$`.
- NO `any` type and NO empty `{}` objects.

EXAMPLES:
User: "extract all persons mentioned with their age and company, plus an executive summary"
Output:
{
  summary: string, // high-level executive summary of the document
  people: [
    {
      name: string,
      age: number?, // age in years if stated
      company: string? // associated company or organization
    }
  ]
}

User: "get all transactions with date, amount, vendor and category (food, travel, tech)"
Output:
[
  {
    transaction_date: date, // date of transaction in YYYY-MM-DD
    amount: number, // total monetary amount
    vendor: string, // merchant or vendor name
    category: "food" | "travel" | "tech" | "other" // transaction category
  }
]

OUTPUT INSTRUCTION:
Return ONLY the raw shape code. No markdown fences, no explanations."""


def build_nl_shape_prompts(user_request: str) -> tuple[str, str]:
    """Generates prompts to convert natural language request into shape language."""
    return NL_SHAPE_SYSTEM_PROMPT, f"Request: {user_request}"


def build_nl_shape_retry_prompts(
    user_request: str, failed_shape: str, error_message: str
) -> tuple[str, str]:
    """Generates retry prompts when inferred shape fails to parse."""
    user_msg = f"""Your previous shape definition failed to parse.

User Request:
{user_request}

Failed Shape:
{failed_shape}

Parser Error:
{error_message}

Please fix the syntax error and output only the valid shape code."""
    return NL_SHAPE_SYSTEM_PROMPT, user_msg
