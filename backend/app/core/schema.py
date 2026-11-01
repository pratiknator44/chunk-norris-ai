"""Schema generator for DocExtract.

Converts a ShapeTree into:
1. Strict JSON Schema for OpenAI / LM Studio structured output (response_format).
2. Dynamic Pydantic validation models (Pydantic v2).
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.core.shape import (
    ArrayNode,
    EnumNode,
    ObjectNode,
    ScalarNode,
    ShapeNode,
    ShapeTree,
)


def shape_node_to_json_schema(node: ShapeNode) -> dict[str, Any]:
    """Converts a ShapeNode to a strict JSON Schema definition."""
    schema: dict[str, Any] = {}

    if isinstance(node, ScalarNode):
        type_mapping = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "date": "string",
        }
        base_type = type_mapping.get(node.kind, "string")
        if node.is_optional:
            schema["type"] = [base_type, "null"]
        else:
            schema["type"] = base_type

        if node.kind == "date":
            schema["format"] = "date"

    elif isinstance(node, EnumNode):
        if node.is_optional:
            schema["type"] = ["string", "null"]
            schema["enum"] = [*node.values, None]
        else:
            schema["type"] = "string"
            schema["enum"] = list(node.values)

    elif isinstance(node, ArrayNode):
        element_schema = shape_node_to_json_schema(node.element_type)
        if node.is_optional:
            schema["type"] = ["array", "null"]
        else:
            schema["type"] = "array"
        schema["items"] = element_schema

    elif isinstance(node, ObjectNode):
        properties: dict[str, Any] = {}
        for key, field_node in node.fields.items():
            properties[key] = shape_node_to_json_schema(field_node)

        if node.is_optional:
            schema["type"] = ["object", "null"]
        else:
            schema["type"] = "object"
        schema["properties"] = properties
        # In OpenAI strict mode, all properties must be listed in required
        schema["required"] = list(properties.keys())
        schema["additionalProperties"] = False

    else:
        raise TypeError(f"Unknown shape node type: {type(node)}")

    if node.description:
        schema["description"] = node.description

    return schema


def shape_tree_to_json_schema(tree: ShapeTree) -> dict[str, Any]:
    """Converts a ShapeTree to an OpenAI-compatible root JSON Schema.

    Top-level arrays are wrapped as { items: [ ... ] }.
    """
    if tree.is_top_level_array:
        array_schema = shape_node_to_json_schema(tree.root)
        return {
            "type": "object",
            "properties": {
                "items": array_schema,
            },
            "required": ["items"],
            "additionalProperties": False,
        }

    root_schema = shape_node_to_json_schema(tree.root)
    # Ensure root is an object schema
    if root_schema.get("type") != "object":
        return {
            "type": "object",
            "properties": {
                "result": root_schema,
            },
            "required": ["result"],
            "additionalProperties": False,
        }
    return root_schema


def shape_node_to_pydantic_type(
    node: ShapeNode, model_name_prefix: str = "Model"
) -> tuple[Any, Any]:
    """Recursively converts a ShapeNode into a (python_type, Field(...)) tuple for Pydantic v2."""
    field_kwargs: dict[str, Any] = {}
    if node.description:
        field_kwargs["description"] = node.description

    if isinstance(node, ScalarNode):
        type_map = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "date": str,  # Keep lenient as str
        }
        py_type = type_map.get(node.kind, str)
        if node.is_optional:
            return py_type | None, Field(default=None, **field_kwargs)
        return py_type, Field(..., **field_kwargs)

    elif isinstance(node, EnumNode):
        # Build Literal type
        literal_type: Any = Literal[tuple(node.values)] if node.values else str
        if node.is_optional:
            return literal_type | None, Field(default=None, **field_kwargs)
        return literal_type, Field(..., **field_kwargs)

    elif isinstance(node, ArrayNode):
        elem_type, _ = shape_node_to_pydantic_type(node.element_type, f"{model_name_prefix}Item")
        list_type: Any = list[elem_type]  # type: ignore[valid-type]
        if node.is_optional:
            return list_type | None, Field(default=None, **field_kwargs)
        return list_type, Field(default_factory=list, **field_kwargs)

    elif isinstance(node, ObjectNode):
        sub_fields: dict[str, Any] = {}
        for key, field_node in node.fields.items():
            child_prefix = f"{model_name_prefix}_{key.capitalize()}"
            sub_fields[key] = shape_node_to_pydantic_type(field_node, child_prefix)

        created = create_model(
            model_name_prefix,
            __config__=ConfigDict(extra="forbid"),
            **sub_fields,
        )

        if node.is_optional:
            return created | None, Field(default=None, **field_kwargs)
        return created, Field(..., **field_kwargs)

    raise TypeError(f"Unknown shape node: {type(node)}")


def shape_tree_to_pydantic_model(
    tree: ShapeTree, model_name: str = "ExtractedDocument"
) -> type[BaseModel]:
    """Generates a dynamic Pydantic v2 model from a ShapeTree."""
    if tree.is_top_level_array:
        items_type, items_field = shape_node_to_pydantic_type(tree.root, f"{model_name}_Items")
        return create_model(
            model_name,
            __config__=ConfigDict(extra="forbid"),
            items=(items_type, items_field),
        )

    if isinstance(tree.root, ObjectNode):
        fields: dict[str, Any] = {}
        for key, node in tree.root.fields.items():
            child_prefix = f"{model_name}_{key.capitalize()}"
            fields[key] = shape_node_to_pydantic_type(node, child_prefix)
        return create_model(
            model_name,
            __config__=ConfigDict(extra="forbid"),
            **fields,
        )

    # Fallback single field
    val_type, val_field = shape_node_to_pydantic_type(tree.root, f"{model_name}_Result")
    return create_model(
        model_name,
        __config__=ConfigDict(extra="forbid"),
        result=(val_type, val_field),
    )


def validate_extracted_data(
    raw_json: dict[str, Any] | list[Any],
    tree: ShapeTree,
    model: type[BaseModel] | None = None,
) -> dict[str, Any] | list[Any]:
    """Validates raw extracted JSON against the generated Pydantic model.

    Unwraps top-level arrays if needed.
    """
    if model is None:
        model = shape_tree_to_pydantic_model(tree)

    if tree.is_top_level_array:
        if isinstance(raw_json, list):
            data_to_validate = {"items": raw_json}
        elif isinstance(raw_json, dict) and "items" in raw_json:
            data_to_validate = raw_json
        else:
            data_to_validate = {"items": [raw_json]}
        validated = model.model_validate(data_to_validate)
        dumped = validated.model_dump()
        return cast(list[Any], dumped.get("items", []))

    if not isinstance(raw_json, dict):
        raw_json = {"result": raw_json}

    validated = model.model_validate(raw_json)
    return validated.model_dump()
