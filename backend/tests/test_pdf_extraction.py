from app.ingestion.pdf import _heading_at, _is_contents_page


def test_detects_two_line_3gpp_clause_heading() -> None:
    assert _heading_at(["5.5.1.1", "General"], 0) == ("5.5.1.1", "General", 2)


def test_does_not_treat_numbered_protocol_text_as_a_heading() -> None:
    assert _heading_at(["1", "1 no key is available (UE to network);"], 0) is None


def test_detects_contents_pages() -> None:
    lines = [
        "Registration procedure ........................................ 325",
        "Definitions .................................................. 30",
        "References ................................................... 23",
        "Foreword ..................................................... 22",
    ]
    assert _is_contents_page(lines)
