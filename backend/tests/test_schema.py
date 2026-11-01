import pytest
from pydantic import ValidationError

from app.core.schema import (
    shape_tree_to_json_schema,
    shape_tree_to_pydantic_model,
    validate_extracted_data,
)
from app.core.shape import parse_shape


def test_schema_generation_scalars():
    tree = parse_shape("{ name: string, age: number?, birth_date: date? }")
    json_schema = shape_tree_to_json_schema(tree)

    assert json_schema["type"] == "object"
    assert "additionalProperties" in json_schema and json_schema["additionalProperties"] is False
    assert set(json_schema["required"]) == {"name", "age", "birth_date"}
    assert json_schema["properties"]["name"]["type"] == "string"
    assert json_schema["properties"]["age"]["type"] == ["number", "null"]
    assert json_schema["properties"]["birth_date"]["type"] == ["string", "null"]
    assert json_schema["properties"]["birth_date"]["format"] == "date"


def test_schema_generation_enums():
    tree = parse_shape('{ status: "active" | "inactive" }')
    json_schema = shape_tree_to_json_schema(tree)
    status_schema = json_schema["properties"]["status"]
    assert status_schema["type"] == "string"
    assert status_schema["enum"] == ["active", "inactive"]


def test_pydantic_model_validation_success():
    tree = parse_shape("""
    {
      user: {
        name: string,
        role: "admin" | "user"?,
        tags: [string]
      }
    }
    """)
    model = shape_tree_to_pydantic_model(tree)

    payload = {
        "user": {
            "name": "Alice",
            "role": "admin",
            "tags": ["developer", "python"],
        }
    }
    validated = model.model_validate(payload)
    assert validated.model_dump() == payload


def test_pydantic_model_validation_failure():
    tree = parse_shape("{ count: integer }")
    model = shape_tree_to_pydantic_model(tree)

    with pytest.raises(ValidationError):
        model.model_validate({"count": "not_an_int"})

    with pytest.raises(ValidationError):
        # extra fields forbidden in strict config
        model.model_validate({"count": 5, "extra": "forbidden"})


def test_top_level_array_validation_and_unwrap():
    tree = parse_shape("[ { id: integer, title: string } ]")
    json_schema = shape_tree_to_json_schema(tree)

    assert json_schema["type"] == "object"
    assert "items" in json_schema["properties"]

    raw_items = [
        {"id": 1, "title": "First"},
        {"id": 2, "title": "Second"},
    ]
    # validate_extracted_data unwraps items to list
    unwrapped = validate_extracted_data(raw_items, tree)
    assert isinstance(unwrapped, list)
    assert len(unwrapped) == 2
    assert unwrapped[0]["id"] == 1
