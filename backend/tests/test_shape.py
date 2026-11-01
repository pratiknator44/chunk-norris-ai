import pytest

from app.core.shape import (
    ArrayNode,
    EnumNode,
    ObjectNode,
    ParseError,
    ScalarNode,
    detect_mode,
    parse_shape,
)


def test_parse_simple_object():
    text = "{ name: string, age: number, is_student: boolean }"
    tree = parse_shape(text)
    assert not tree.is_top_level_array
    assert isinstance(tree.root, ObjectNode)
    assert len(tree.root.fields) == 3
    assert isinstance(tree.root.fields["name"], ScalarNode)
    assert tree.root.fields["name"].kind == "string"
    assert isinstance(tree.root.fields["age"], ScalarNode)
    assert tree.root.fields["age"].kind == "number"


def test_parse_optional_and_date():
    text = "{ created_at: date?, notes: string? }"
    tree = parse_shape(text)
    assert isinstance(tree.root, ObjectNode)
    assert tree.root.fields["created_at"].is_optional is True
    assert isinstance(tree.root.fields["created_at"], ScalarNode)
    assert tree.root.fields["created_at"].kind == "date"
    assert tree.root.fields["notes"].is_optional is True


def test_parse_enums():
    text = '{ status: "open" | "closed" | "pending" }'
    tree = parse_shape(text)
    assert isinstance(tree.root, ObjectNode)
    status_node = tree.root.fields["status"]
    assert isinstance(status_node, EnumNode)
    assert status_node.values == ["open", "closed", "pending"]


def test_parse_nested_array_of_objects():
    text = """
    {
      company: string,
      employees: [
        {
          name: string,
          status: "active" | "inactive",
          age: integer? // age in full years
        }
      ]
    }
    """
    tree = parse_shape(text)
    assert isinstance(tree.root, ObjectNode)
    emp_node = tree.root.fields["employees"]
    assert isinstance(emp_node, ArrayNode)
    assert isinstance(emp_node.element_type, ObjectNode)
    elem = emp_node.element_type
    assert isinstance(elem.fields["status"], EnumNode)
    assert elem.fields["age"].description == "age in full years"
    assert elem.fields["age"].is_optional is True


def test_parse_top_level_array():
    text = "[ { name: string, score: number } ]"
    tree = parse_shape(text)
    assert tree.is_top_level_array is True
    assert isinstance(tree.root, ArrayNode)
    assert isinstance(tree.root.element_type, ObjectNode)
    assert "name" in tree.root.element_type.fields


def test_disallow_any():
    with pytest.raises(ParseError) as exc_info:
        parse_shape("{ data: any }")
    assert "any" in str(exc_info.value).lower()


def test_disallow_empty_object():
    with pytest.raises(ParseError) as exc_info:
        parse_shape("{ }")
    assert "empty object" in str(exc_info.value).lower()


def test_detect_mode_valid_shape():
    text = "{ count: number }"
    mode, info = detect_mode(text)
    assert mode == "shape"
    assert info["ok"] is True


def test_detect_mode_typo_in_shape():
    text = "{ count: unsupported_type_xyz }"
    mode, info = detect_mode(text)
    assert mode == "shape"
    assert info["ok"] is False
    assert len(info["errors"]) > 0


def test_detect_mode_plain_english():
    text = "Extract a list of all countries mentioned and character names"
    mode, info = detect_mode(text)
    assert mode == "natural_language"
    assert info["ok"] is False
    assert info["reason"] == "plain_english"
