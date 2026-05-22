import pytest
from inference.formatter.formatter import ReviewComment, parse_review_comments


def test_valid_json_array():
    raw = '[{"file": "Foo.java", "line": 10, "severity": "warning", "comment": "Use Optional here."}]'
    result = parse_review_comments(raw)
    assert len(result) == 1
    assert result[0] == ReviewComment(file="Foo.java", line=10, severity="warning", comment="Use Optional here.")


def test_valid_json_multiple_items():
    raw = '[{"file": "A.java", "line": 1, "severity": "nit", "comment": "Rename this."}, {"file": "B.java", "line": 5, "severity": "blocking", "comment": "Null pointer risk."}]'
    result = parse_review_comments(raw)
    assert len(result) == 2
    assert result[0].severity == "nit"
    assert result[1].severity == "blocking"


def test_valid_json_single_object():
    raw = '{"file": "Foo.java", "line": 3, "severity": "blocking", "comment": "This will NPE."}'
    result = parse_review_comments(raw)
    assert len(result) == 1
    assert result[0].file == "Foo.java"


def test_preamble_and_postamble_stripped():
    raw = 'Here is my review:\n[{"file": "X.java", "line": 2, "severity": "nit", "comment": "Trailing whitespace."}]\nLet me know if you have questions.'
    result = parse_review_comments(raw)
    assert len(result) == 1
    assert result[0].file == "X.java"


def test_malformed_json_falls_back():
    raw = "This looks fine but consider renaming the variable for clarity."
    result = parse_review_comments(raw, fallback_file="Foo.java", fallback_line=7)
    assert len(result) == 1
    assert result[0].severity == "nit"
    assert result[0].file == "Foo.java"
    assert result[0].line == 7
    assert result[0].comment == raw.strip()


def test_empty_string_returns_empty():
    assert parse_review_comments("") == []


def test_whitespace_only_returns_empty():
    assert parse_review_comments("   \n\t  ") == []


def test_missing_required_field_skipped():
    # Missing "comment" field — item should be silently dropped
    raw = '[{"file": "Foo.java", "line": 1, "severity": "nit"}]'
    result = parse_review_comments(raw)
    assert result == []


def test_wrong_severity_skipped():
    raw = '[{"file": "Foo.java", "line": 1, "severity": "critical", "comment": "Bad."}]'
    result = parse_review_comments(raw)
    assert result == []


def test_mixed_valid_and_invalid_items():
    raw = '[{"file": "A.java", "line": 1, "severity": "nit", "comment": "Ok."}, {"file": "B.java", "line": 2, "severity": "unknown", "comment": "Bad severity."}, {"file": "C.java", "line": 3, "severity": "warning", "comment": "Missing check."}]'
    result = parse_review_comments(raw)
    assert len(result) == 2
    assert result[0].file == "A.java"
    assert result[1].file == "C.java"


def test_never_raises_on_garbage():
    garbage_inputs = [
        "}{][ not json at all",
        "[[[",
        '{"severity": null, "file": null, "line": null, "comment": null}',
        "None",
        "0",
    ]
    for raw in garbage_inputs:
        result = parse_review_comments(raw)
        assert isinstance(result, list)
