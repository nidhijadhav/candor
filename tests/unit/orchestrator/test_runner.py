from unittest.mock import MagicMock, patch
import requests
import pytest

from inference.formatter.formatter import ReviewComment
from orchestrator.run import review_diff

SINGLE_FILE_DIFF = """\
diff --git a/Foo.java b/Foo.java
--- a/Foo.java
+++ b/Foo.java
@@ -1,3 +1,3 @@
-int x = 0;
+int x = 1;
"""

MULTI_FILE_DIFF = """\
diff --git a/Foo.java b/Foo.java
--- a/Foo.java
+++ b/Foo.java
@@ -1,3 +1,3 @@
-int x = 0;
+int x = 1;
diff --git a/Bar.java b/Bar.java
--- a/Bar.java
+++ b/Bar.java
@@ -5,3 +5,3 @@
-String s = null;
+String s = "";
"""

_COMMENT_JSON = '[{"file": "Foo.java", "line": 1, "severity": "nit", "comment": "Rename x."}]'
_EMPTY_JSON = "[]"


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


# --- call count ---

def test_single_chunk_calls_inference_once():
    with patch("orchestrator.run.requests.post", return_value=_mock_response(_COMMENT_JSON)) as mock_post:
        review_diff(SINGLE_FILE_DIFF)
    assert mock_post.call_count == 1


def test_multi_chunk_calls_inference_per_chunk():
    with patch("orchestrator.run.requests.post", return_value=_mock_response(_EMPTY_JSON)) as mock_post:
        review_diff(MULTI_FILE_DIFF)
    assert mock_post.call_count == 2


def test_empty_diff_makes_no_inference_calls():
    with patch("orchestrator.run.requests.post") as mock_post:
        result = review_diff("")
    assert mock_post.call_count == 0
    assert result == []


# --- deduplication ---

def test_deduplication_keeps_highest_severity():
    responses = [
        '[{"file": "Foo.java", "line": 5, "severity": "nit", "comment": "Minor."}]',
        '[{"file": "Foo.java", "line": 5, "severity": "blocking", "comment": "Critical."}]',
    ]
    side_effects = [_mock_response(r) for r in responses]
    with patch("orchestrator.run.requests.post", side_effect=side_effects):
        result = review_diff(MULTI_FILE_DIFF)
    foo_line5 = [c for c in result if c.file == "Foo.java" and c.line == 5]
    assert len(foo_line5) == 1
    assert foo_line5[0].severity == "blocking"


def test_deduplication_keeps_warning_over_nit():
    responses = [
        '[{"file": "Foo.java", "line": 2, "severity": "warning", "comment": "Check null."}]',
        '[{"file": "Foo.java", "line": 2, "severity": "nit", "comment": "Style."}]',
    ]
    side_effects = [_mock_response(r) for r in responses]
    with patch("orchestrator.run.requests.post", side_effect=side_effects):
        result = review_diff(MULTI_FILE_DIFF)
    matches = [c for c in result if c.file == "Foo.java" and c.line == 2]
    assert len(matches) == 1
    assert matches[0].severity == "warning"


def test_different_file_line_pairs_not_deduplicated():
    responses = [
        '[{"file": "Foo.java", "line": 1, "severity": "nit", "comment": "A."}]',
        '[{"file": "Bar.java", "line": 5, "severity": "nit", "comment": "B."}]',
    ]
    side_effects = [_mock_response(r) for r in responses]
    with patch("orchestrator.run.requests.post", side_effect=side_effects):
        result = review_diff(MULTI_FILE_DIFF)
    assert len(result) == 2


# --- inference unavailable ---

def test_connection_error_returns_empty_list(capsys):
    with patch("orchestrator.run.requests.post", side_effect=requests.exceptions.ConnectionError()):
        result = review_diff(SINGLE_FILE_DIFF)
    assert result == []
    assert "unavailable" in capsys.readouterr().err


def test_timeout_returns_empty_list(capsys):
    with patch("orchestrator.run.requests.post", side_effect=requests.exceptions.Timeout()):
        result = review_diff(SINGLE_FILE_DIFF)
    assert result == []
    assert "timed out" in capsys.readouterr().err


def test_http_error_returns_empty_list(capsys):
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    with patch("orchestrator.run.requests.post", return_value=resp):
        result = review_diff(SINGLE_FILE_DIFF)
    assert result == []
    err = capsys.readouterr().err
    assert "failed" in err


# --- return type ---

def test_returns_list_of_review_comments():
    with patch("orchestrator.run.requests.post", return_value=_mock_response(_COMMENT_JSON)):
        result = review_diff(SINGLE_FILE_DIFF)
    assert isinstance(result, list)
    assert all(isinstance(c, ReviewComment) for c in result)
