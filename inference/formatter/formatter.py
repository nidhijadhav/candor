import json
import re
from dataclasses import dataclass
from typing import Literal

VALID_SEVERITIES = {"nit", "warning", "blocking"}


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: Literal["nit", "warning", "blocking"]
    comment: str


def _extract_json(text: str) -> str:
    """Return the first [...] or {...} block found in text, stripping preamble/postamble."""
    for open_char, close_char in [("[", "]"), ("{", "}")]:
        start = text.find(open_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return ""


def parse_review_comments(
    raw_output: str,
    fallback_file: str = "",
    fallback_line: int = 0,
) -> list[ReviewComment]:
    if not raw_output or not raw_output.strip():
        return []

    try:
        json_str = _extract_json(raw_output)
        if not json_str:
            raise ValueError("no JSON block found")

        parsed = json.loads(json_str)
        # Normalise single object to list
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise ValueError("expected JSON array or object")

        comments = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            file = item.get("file")
            line = item.get("line")
            severity = item.get("severity")
            comment = item.get("comment")

            if not all([file is not None, line is not None, severity is not None, comment is not None]):
                continue
            if severity not in VALID_SEVERITIES:
                continue

            comments.append(ReviewComment(
                file=str(file),
                line=int(line),
                severity=severity,
                comment=str(comment),
            ))

        return comments

    except Exception:
        return [ReviewComment(
            file=fallback_file,
            line=fallback_line,
            severity="nit",
            comment=raw_output.strip(),
        )]
