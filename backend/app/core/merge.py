"""Recursive document merger for DocExtract.

Merges chunk extraction results across chunks into a single unified JSON result.
Rules:
  - Scalars: first non-null/non-empty value in chunk order.
  - Objects: recursive merge per field.
  - Arrays of scalars: union with case-insensitive deduplication, preserving first-seen order.
  - Arrays of objects: concatenation and key-based merging (filling nulls) if an obvious key
    exists (e.g. name, id), otherwise deduplicating by canonical JSON.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.shape import (
    ArrayNode,
    EnumNode,
    ObjectNode,
    ScalarNode,
    ShapeNode,
    ShapeTree,
)

CANDIDATE_KEYS = ["id", "name", "title", "code", "email", "key"]


def _find_entity_key(obj_node: ObjectNode) -> str | None:
    """Finds an identifying key field name in an ObjectNode if one exists."""
    for cand in CANDIDATE_KEYS:
        if cand in obj_node.fields:
            return cand
    return None


def _canonical_json(obj: Any) -> str:
    """Produces a deterministic JSON string for object deduplication."""
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(obj)


def _merge_scalar(values: list[Any]) -> Any:
    """Returns the first non-null, non-empty value in chunk order."""
    for val in values:
        if val is not None and val != "":
            return val
    return None


def _merge_scalar_array(values_list: list[list[Any]]) -> list[Any]:
    """Union and case-insensitive deduplication for arrays of scalars."""
    merged: list[Any] = []
    seen: set[str] = set()

    for chunk_list in values_list:
        if not isinstance(chunk_list, list):
            continue
        for item in chunk_list:
            if item is None:
                continue
            item_str = str(item).strip()
            if not item_str:
                continue
            normalized = item_str.casefold()
            if normalized not in seen:
                seen.add(normalized)
                merged.append(item)
    return merged


def _merge_object_nodes(objects: list[dict[str, Any]], obj_node: ObjectNode) -> dict[str, Any]:
    """Recursively merges a list of dictionary representations conforming to obj_node."""
    merged: dict[str, Any] = {}

    for field_name, child_node in obj_node.fields.items():
        field_values = [
            obj.get(field_name) for obj in objects if isinstance(obj, dict) and field_name in obj
        ]
        merged[field_name] = _merge_node_values(field_values, child_node)

    return merged


def _merge_object_array(
    chunks_of_objects: list[list[dict[str, Any]]], elem_node: ObjectNode
) -> list[dict[str, Any]]:
    """Merges arrays of objects with entity-key matching or canonical JSON deduplication."""
    key_field = _find_entity_key(elem_node)
    all_items: list[dict[str, Any]] = []

    for chunk in chunks_of_objects:
        if not isinstance(chunk, list):
            continue
        for item in chunk:
            if isinstance(item, dict):
                all_items.append(item)

    if not all_items:
        return []

    # If an entity key exists (e.g., 'name', 'id'), group and merge objects sharing the same key
    if key_field:
        grouped: dict[str, list[dict[str, Any]]] = {}
        order: list[str] = []
        unkeyed: list[dict[str, Any]] = []

        for item in all_items:
            key_val = item.get(key_field)
            if key_val is not None and str(key_val).strip() != "":
                norm_key = str(key_val).strip().casefold()
                if norm_key not in grouped:
                    grouped[norm_key] = []
                    order.append(norm_key)
                grouped[norm_key].append(item)
            else:
                unkeyed.append(item)

        results: list[dict[str, Any]] = []
        for norm_key in order:
            group = grouped[norm_key]
            # Recursively merge objects with the same key (filling missing/null fields)
            merged_item = _merge_object_nodes(group, elem_node)
            results.append(merged_item)

        # Append unkeyed items (deduplicated by canonical JSON)
        seen_json = {_canonical_json(r) for r in results}
        for item in unkeyed:
            c = _canonical_json(item)
            if c not in seen_json:
                seen_json.add(c)
                results.append(item)

        return results

    # If no obvious key, deduplicate by canonical JSON
    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in all_items:
        c = _canonical_json(item)
        if c not in seen:
            seen.add(c)
            deduped.append(item)
    return deduped


def _merge_node_values(values: list[Any], node: ShapeNode) -> Any:
    """Dispatches merge strategy based on ShapeNode type."""
    if isinstance(node, (ScalarNode, EnumNode)):
        return _merge_scalar(values)

    elif isinstance(node, ArrayNode):
        if isinstance(node.element_type, (ScalarNode, EnumNode)):
            return _merge_scalar_array(values)
        elif isinstance(node.element_type, ObjectNode):
            return _merge_object_array(values, node.element_type)
        else:
            # Nested array
            combined = []
            for v in values:
                if isinstance(v, list):
                    combined.extend(v)
            return combined

    elif isinstance(node, ObjectNode):
        non_null_objs = [v for v in values if isinstance(v, dict)]
        if not non_null_objs:
            return None if node.is_optional else {}
        return _merge_object_nodes(non_null_objs, node)

    return None


def merge_results(
    chunk_results: list[dict[str, Any] | list[Any]],
    tree: ShapeTree,
) -> dict[str, Any] | list[Any]:
    """Combines chunk extraction results into a final single JSON document.

    Respects the shape structure defined by tree.
    """
    if not chunk_results:
        if tree.is_top_level_array:
            return []
        if isinstance(tree.root, ObjectNode):
            return {k: None if v.is_optional else None for k, v in tree.root.fields.items()}
        return {}

    # Handle top-level array: [ ... ]
    if tree.is_top_level_array:
        # Each chunk result might be a list or {"items": [...]}
        flattened_chunks: list[list[Any]] = []
        for res in chunk_results:
            if isinstance(res, list):
                flattened_chunks.append(res)
            elif isinstance(res, dict) and "items" in res and isinstance(res["items"], list):
                flattened_chunks.append(res["items"])
            elif isinstance(res, dict):
                flattened_chunks.append([res])

        if isinstance(tree.root, ArrayNode):
            if isinstance(tree.root.element_type, ObjectNode):
                return _merge_object_array(flattened_chunks, tree.root.element_type)
            elif isinstance(tree.root.element_type, (ScalarNode, EnumNode)):
                return _merge_scalar_array(flattened_chunks)

        # Fallback list union
        merged_list = []
        seen = set()
        for chunk in flattened_chunks:
            for item in chunk:
                c = _canonical_json(item)
                if c not in seen:
                    seen.add(c)
                    merged_list.append(item)
        return merged_list

    # Top-level object
    if isinstance(tree.root, ObjectNode):
        objs = [res for res in chunk_results if isinstance(res, dict)]
        return _merge_object_nodes(objs, tree.root)

    # Fallback
    fallback = _merge_scalar(chunk_results)
    if isinstance(fallback, (dict, list)):
        return fallback
    return {"result": fallback}
