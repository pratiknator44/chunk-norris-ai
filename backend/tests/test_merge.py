from app.core.merge import merge_results
from app.core.shape import parse_shape


def test_merge_scalars():
    tree = parse_shape("{ title: string, count: integer? }")
    chunks = [
        {"title": None, "count": None},
        {"title": "My Doc", "count": 10},
        {"title": "Another Title", "count": 20},
    ]
    merged = merge_results(chunks, tree)
    assert merged["title"] == "My Doc"  # First non-null
    assert merged["count"] == 10  # First non-null


def test_merge_scalar_arrays_dedupe_case_insensitive():
    tree = parse_shape("{ tags: [string] }")
    chunks = [
        {"tags": ["AI", "python", "fastapi"]},
        {"tags": ["Python", "FASTAPI", "Docling"]},
    ]
    merged = merge_results(chunks, tree)
    # "Python" and "FASTAPI" should be deduplicated (preserving first seen "python" and "fastapi")
    assert merged["tags"] == ["AI", "python", "fastapi", "Docling"]


def test_merge_object_arrays_with_key_filling_nulls():
    tree = parse_shape("""
    {
      people: [
        {
          name: string,
          age: integer?,
          city: string?
        }
      ]
    }
    """)
    chunks = [
        {
            "people": [
                {"name": "Alice", "age": 30, "city": None},
                {"name": "Bob", "age": None, "city": "London"},
            ]
        },
        {
            "people": [
                {"name": "alice", "age": None, "city": "Paris"},  # Same name -> fills city
                {"name": "Charlie", "age": 45, "city": "Berlin"},
            ]
        },
    ]
    merged = merge_results(chunks, tree)
    people = merged["people"]
    assert len(people) == 3

    alice = next(p for p in people if p["name"].lower() == "alice")
    assert alice["age"] == 30
    assert alice["city"] == "Paris"  # Filled from chunk 2!


def test_merge_top_level_array():
    tree = parse_shape("[ { id: integer, title: string } ]")
    chunks = [
        [{"id": 1, "title": "Doc 1"}],
        [{"id": 2, "title": "Doc 2"}],
        [{"id": 1, "title": "Doc 1"}],  # Duplicate by id
    ]
    merged = merge_results(chunks, tree)
    assert isinstance(merged, list)
    assert len(merged) == 2
    assert merged[0]["id"] == 1
    assert merged[1]["id"] == 2
