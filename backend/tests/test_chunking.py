from app.core.chunking import split_document


def test_split_document_short_text():
    text = "Short text under max chars."
    chunks = split_document(text, max_chars=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_document_empty():
    assert split_document("") == []
    assert split_document("   \n\n  ") == []


def test_split_document_paragraphs():
    p1 = "Paragraph one with some information."
    p2 = "Paragraph two with additional details."
    p3 = "Paragraph three concluding the report."
    text = f"{p1}\n\n{p2}\n\n{p3}"

    # Set max_chars small enough to force paragraph splitting
    chunks = split_document(text, max_chars=60, overlap_chars=0)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 60


def test_split_document_overlap():
    p1 = "Alpha beta gamma delta epsilon."
    p2 = "Zeta eta theta iota kappa."
    p3 = "Lambda mu nu xi omicron."
    text = f"{p1}\n\n{p2}\n\n{p3}"

    chunks = split_document(text, max_chars=40, overlap_chars=15)
    assert len(chunks) >= 2
    # Verify second chunk includes content from the end of the first chunk
    assert len(chunks[1]) > 0


def test_split_long_paragraph_without_cutting_words():
    long_para = "word " * 50  # 250 characters
    chunks = split_document(long_para, max_chars=50, overlap_chars=0)
    assert len(chunks) >= 5
    for c in chunks:
        assert len(c) <= 50
        # Words shouldn't be broken in half
        assert not c.startswith("ord ")
