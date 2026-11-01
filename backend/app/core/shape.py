"""Shape language parser for DocExtract.

Parses concise TypeScript-like shape syntax into an AST (ShapeTree).
Syntax supported:
  - Primitives: string, number, integer, boolean, date
  - String literal enums: "a" | "b" | "c"
  - Optionality: T?
  - Arrays: [T] or T[]
  - Objects: { key: T, ... } (keys unquoted or quoted, comma/semicolon/newline separated)
  - Descriptions: // inline comments
  - Top-level arrays: [ { name: string } ] (wrapped internally as { items: [...] })
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

KEY_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_DEPTH = 5
MAX_FIELDS = 100

PRIMITIVE_TYPES = {"string", "number", "integer", "boolean", "date"}


class ParseError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Line {line}, Col {col}: {message}")
        self.message = message
        self.line = line
        self.col = col

    def to_dict(self) -> dict[str, Any]:
        return {"line": self.line, "col": self.col, "message": self.message}


# ----------------------------------------------------------------------
# AST Nodes
# ----------------------------------------------------------------------


@dataclass
class ShapeNode:
    description: str | None = None
    is_optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class ScalarNode(ShapeNode):
    kind: Literal["string", "number", "integer", "boolean", "date"] = "string"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "scalar",
            "kind": self.kind,
            "optional": self.is_optional,
            "description": self.description,
        }


@dataclass
class EnumNode(ShapeNode):
    values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "enum",
            "values": self.values,
            "optional": self.is_optional,
            "description": self.description,
        }


@dataclass
class ArrayNode(ShapeNode):
    element_type: ShapeNode = field(default_factory=ScalarNode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "array",
            "element": self.element_type.to_dict(),
            "optional": self.is_optional,
            "description": self.description,
        }


@dataclass
class ObjectNode(ShapeNode):
    fields: dict[str, ShapeNode] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "object",
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "optional": self.is_optional,
            "description": self.description,
        }


@dataclass
class ShapeTree:
    root: ShapeNode
    is_top_level_array: bool = False
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_top_level_array": self.is_top_level_array,
            "root": self.root.to_dict(),
        }


# ----------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


class Tokenizer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(text)

    def _peek_char(self) -> str:
        if self.pos >= self.length:
            return ""
        return self.text[self.pos]

    def _next_char(self) -> str:
        if self.pos >= self.length:
            return ""
        ch = self.text[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < self.length:
            ch = self._peek_char()

            # Whitespace
            if ch.isspace():
                self._next_char()
                continue

            start_line = self.line
            start_col = self.col

            # Single-line comment: // comment
            if ch == "/" and self.pos + 1 < self.length and self.text[self.pos + 1] == "/":
                self._next_char()
                self._next_char()
                comment_text = []
                while self.pos < self.length and self._peek_char() != "\n":
                    comment_text.append(self._next_char())
                tokens.append(
                    Token("COMMENT", "".join(comment_text).strip(), start_line, start_col)
                )
                continue

            # String literals: "..." or '...'
            if ch in ('"', "'"):
                quote_char = self._next_char()
                str_chars = []
                while self.pos < self.length:
                    curr = self._next_char()
                    if curr == quote_char:
                        break
                    if curr == "\\":
                        escaped = self._next_char()
                        str_chars.append(escaped)
                    else:
                        str_chars.append(curr)
                tokens.append(Token("STRING_LITERAL", "".join(str_chars), start_line, start_col))
                continue

            # Single-character tokens
            if ch == "{":
                self._next_char()
                tokens.append(Token("LBRACE", "{", start_line, start_col))
            elif ch == "}":
                self._next_char()
                tokens.append(Token("RBRACE", "}", start_line, start_col))
            elif ch == "[":
                self._next_char()
                tokens.append(Token("LBRACKET", "[", start_line, start_col))
            elif ch == "]":
                self._next_char()
                tokens.append(Token("RBRACKET", "]", start_line, start_col))
            elif ch == ":":
                self._next_char()
                tokens.append(Token("COLON", ":", start_line, start_col))
            elif ch == "|":
                self._next_char()
                tokens.append(Token("PIPE", "|", start_line, start_col))
            elif ch == "?":
                self._next_char()
                tokens.append(Token("QUESTION", "?", start_line, start_col))
            elif ch == ",":
                self._next_char()
                tokens.append(Token("COMMA", ",", start_line, start_col))
            elif ch == ";":
                self._next_char()
                tokens.append(Token("SEMICOLON", ";", start_line, start_col))
            # Identifiers
            elif ch.isalpha() or ch == "_":
                ident_chars = []
                while self.pos < self.length and (
                    self._peek_char().isalnum() or self._peek_char() == "_"
                ):
                    ident_chars.append(self._next_char())
                tokens.append(Token("IDENT", "".join(ident_chars), start_line, start_col))
            else:
                self._next_char()
                raise ParseError(f"Unexpected character '{ch}'", start_line, start_col)

        tokens.append(Token("EOF", "", self.line, self.col))
        return tokens


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------


class Parser:
    def __init__(self, tokens: list[Token], raw_text: str):
        self.tokens = tokens
        self.raw_text = raw_text
        self.pos = 0
        self.field_count = 0

    def _curr(self) -> Token:
        return self.tokens[self.pos]

    def _peek_next(self) -> Token:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.tokens[-1]

    def _consume(self, kind: str | None = None) -> Token:
        token = self._curr()
        if kind and token.kind != kind:
            raise ParseError(
                f"Expected {kind}, got '{token.value or token.kind}'",
                token.line,
                token.col,
            )
        self.pos += 1
        return token

    def _skip_comments(self) -> list[str]:
        comments: list[str] = []
        while self._curr().kind == "COMMENT":
            comments.append(self._curr().value)
            self._consume("COMMENT")
        return comments

    def parse(self) -> ShapeTree:
        self._skip_comments()
        curr = self._curr()

        if curr.kind == "EOF":
            raise ParseError("Empty shape definition", curr.line, curr.col)

        is_top_level_array = False

        # Top-level array: [ ... ]
        if curr.kind == "LBRACKET":
            self._consume("LBRACKET")
            element_node = self._parse_type(depth=1)
            self._consume("RBRACKET")
            self._skip_comments()
            if self._curr().kind != "EOF":
                raise ParseError(
                    f"Unexpected trailing token '{self._curr().value or self._curr().kind}'",
                    self._curr().line,
                    self._curr().col,
                )
            is_top_level_array = True
            root = ArrayNode(element_type=element_node)
            return ShapeTree(
                root=root,
                is_top_level_array=is_top_level_array,
                raw_text=self.raw_text,
            )

        # Top-level object: { ... }
        if curr.kind == "LBRACE":
            root_node: ShapeNode = self._parse_object(depth=1)
            # Check for trailing brackets: { ... }[]
            if self._curr().kind == "LBRACKET":
                self._consume("LBRACKET")
                self._consume("RBRACKET")
                is_top_level_array = True
                root_node = ArrayNode(element_type=root_node)

            self._skip_comments()
            if self._curr().kind != "EOF":
                raise ParseError(
                    f"Unexpected trailing token '{self._curr().value or self._curr().kind}'",
                    self._curr().line,
                    self._curr().col,
                )
            return ShapeTree(
                root=root_node,
                is_top_level_array=is_top_level_array,
                raw_text=self.raw_text,
            )

        raise ParseError(
            f"Shape must begin with '{{' or '[' (got '{curr.value or curr.kind}')",
            curr.line,
            curr.col,
        )

    def _parse_object(self, depth: int) -> ObjectNode:
        if depth > MAX_DEPTH:
            raise ParseError(
                f"Maximum nesting depth of {MAX_DEPTH} exceeded",
                self._curr().line,
                self._curr().col,
            )

        open_brace = self._consume("LBRACE")
        fields: dict[str, ShapeNode] = {}

        while self._curr().kind != "RBRACE":
            pre_comments = self._skip_comments()

            if self._curr().kind == "RBRACE":
                break

            if self._curr().kind == "EOF":
                raise ParseError(
                    "Unterminated object, missing '}'",
                    open_brace.line,
                    open_brace.col,
                )

            # Field key: IDENT or STRING_LITERAL
            key_token = self._curr()
            if key_token.kind in ("IDENT", "STRING_LITERAL"):
                field_key = key_token.value
                self._consume(key_token.kind)
            else:
                raise ParseError(
                    f"Expected field name, got '{key_token.value or key_token.kind}'",
                    key_token.line,
                    key_token.col,
                )

            if not KEY_REGEX.match(field_key):
                raise ParseError(
                    f"Invalid field name '{field_key}'. Must match ^[A-Za-z_][A-Za-z0-9_]*$",
                    key_token.line,
                    key_token.col,
                )

            self.field_count += 1
            if self.field_count > MAX_FIELDS:
                raise ParseError(
                    f"Maximum allowed fields ({MAX_FIELDS}) exceeded",
                    key_token.line,
                    key_token.col,
                )

            self._consume("COLON")

            # Field type
            field_node = self._parse_type(depth=depth + 1)

            # Trailing inline comments on the same line or before next field
            post_comments = self._skip_comments()
            desc = " ".join(pre_comments + post_comments).strip() or None
            if desc:
                field_node.description = desc

            fields[field_key] = field_node

            # Optional separator: comma or semicolon
            if self._curr().kind in ("COMMA", "SEMICOLON"):
                self._consume()

            self._skip_comments()

        self._consume("RBRACE")

        if not fields:
            raise ParseError(
                "Empty object '{}' is not allowed. Concrete fields are required.",
                open_brace.line,
                open_brace.col,
            )

        return ObjectNode(fields=fields)

    def _parse_type(self, depth: int) -> ShapeNode:
        if depth > MAX_DEPTH:
            raise ParseError(
                f"Maximum nesting depth of {MAX_DEPTH} exceeded",
                self._curr().line,
                self._curr().col,
            )

        token = self._curr()

        # Disallow 'any'
        if token.kind == "IDENT" and token.value.lower() == "any":
            raise ParseError(
                "Type 'any' is not permitted in strict mode. Provide a concrete shape.",
                token.line,
                token.col,
            )

        # 1. Array via bracket prefix: [ T ]
        if token.kind == "LBRACKET":
            self._consume("LBRACKET")
            element_type = self._parse_type(depth=depth + 1)
            self._consume("RBRACKET")
            is_opt = self._check_optional()
            return ArrayNode(element_type=element_type, is_optional=is_opt)

        # 2. Nested Object: { ... }
        if token.kind == "LBRACE":
            obj_node = self._parse_object(depth=depth)
            # Support postfix array: { ... }[]
            if self._curr().kind == "LBRACKET":
                self._consume("LBRACKET")
                self._consume("RBRACKET")
                is_opt = self._check_optional()
                return ArrayNode(element_type=obj_node, is_optional=is_opt)
            obj_node.is_optional = self._check_optional()
            return obj_node

        # 3. String literal enum: "open" | "closed"
        if token.kind == "STRING_LITERAL":
            enum_values = [token.value]
            self._consume("STRING_LITERAL")
            while self._curr().kind == "PIPE":
                self._consume("PIPE")
                val_tok = self._consume("STRING_LITERAL")
                enum_values.append(val_tok.value)

            is_opt = self._check_optional()
            # Postfix array: ("a" | "b")[]
            if self._curr().kind == "LBRACKET":
                self._consume("LBRACKET")
                self._consume("RBRACKET")
                enum_node = EnumNode(values=enum_values, is_optional=False)
                is_arr_opt = self._check_optional()
                return ArrayNode(element_type=enum_node, is_optional=is_arr_opt)

            return EnumNode(values=enum_values, is_optional=is_opt)

        # 4. Primitive scalar or postfix array: string, number, string[]
        if token.kind == "IDENT":
            type_name = token.value.lower()
            if type_name not in PRIMITIVE_TYPES:
                valid_types = ", ".join(sorted(PRIMITIVE_TYPES))
                raise ParseError(
                    f"Unsupported type '{token.value}'. "
                    f"Expected one of: {valid_types}, an object, or an enum union.",
                    token.line,
                    token.col,
                )
            self._consume("IDENT")

            # Check for postfix array: T[]
            if self._curr().kind == "LBRACKET":
                self._consume("LBRACKET")
                self._consume("RBRACKET")
                is_opt = self._check_optional()
                elem = ScalarNode(kind=type_name)  # type: ignore
                return ArrayNode(element_type=elem, is_optional=is_opt)

            is_opt = self._check_optional()
            return ScalarNode(kind=type_name, is_optional=is_opt)  # type: ignore

        raise ParseError(
            f"Expected type specification, got '{token.value or token.kind}'",
            token.line,
            token.col,
        )

    def _check_optional(self) -> bool:
        if self._curr().kind == "QUESTION":
            self._consume("QUESTION")
            return True
        return False


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


def parse_shape(text: str) -> ShapeTree:
    """Parses shape language text into a ShapeTree. Raises ParseError on invalid syntax."""
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens, text)
    return parser.parse()


def detect_mode(text: str) -> tuple[Literal["shape", "natural_language"], dict[str, Any]]:
    """Detects whether text is shape language or natural language.

    Algorithm:
    1. Try parsing as shape language.
    2. If successful -> ("shape", {"ok": True, "tree": ...})
    3. If failed:
       - If trimmed text starts with '{' or '[', stays in shape mode with parse errors.
       - Otherwise, returns ("natural_language", {"ok": False, "reason": "plain_english"}).
    """
    stripped = text.strip()
    try:
        tree = parse_shape(stripped)
        return "shape", {"ok": True, "tree": tree.to_dict()}
    except ParseError as err:
        if stripped.startswith("{") or stripped.startswith("["):
            return "shape", {"ok": False, "errors": [err.to_dict()]}
        return "natural_language", {
            "ok": False,
            "reason": "plain_english",
            "fallback_error": err.to_dict(),
        }
