import argparse
import dataclasses
import json
import sys

import requests

from inference.formatter.formatter import ReviewComment, parse_review_comments
from orchestrator.chunker.chunker import DiffChunk, parse_diff
from orchestrator.prompt.assembler import assemble_prompt

_SEVERITY_RANK = {"nit": 0, "warning": 1, "blocking": 2}


def _call_inference(
    messages: list[dict],
    inference_url: str,
    temperature: float,
    max_tokens: int,
) -> str:
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(inference_url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _deduplicate(comments: list[ReviewComment]) -> list[ReviewComment]:
    """Keep the highest-severity comment for each (file, line) pair."""
    best: dict[tuple[str, int], ReviewComment] = {}
    for c in comments:
        key = (c.file, c.line)
        if key not in best or _SEVERITY_RANK[c.severity] > _SEVERITY_RANK[best[key].severity]:
            best[key] = c
    return list(best.values())


def review_diff(
    diff: str,
    guidelines: str = "",
    inference_url: str = "http://127.0.0.1:8080/v1/chat/completions",
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> list[ReviewComment]:
    chunks: list[DiffChunk] = parse_diff(diff)
    if not chunks:
        return []

    all_comments: list[ReviewComment] = []

    for chunk in chunks:
        messages = assemble_prompt(chunk, guidelines=guidelines)
        try:
            raw = _call_inference(messages, inference_url, temperature, max_tokens)
        except requests.exceptions.ConnectionError:
            print(f"Error: inference server unavailable at {inference_url}", file=sys.stderr)
            return []
        except requests.exceptions.Timeout:
            print(f"Error: inference server timed out at {inference_url}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error: inference request failed: {e}", file=sys.stderr)
            return []

        comments = parse_review_comments(raw, fallback_file=chunk.file, fallback_line=0)
        all_comments.extend(comments)

    return _deduplicate(all_comments)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run Candor code review on a diff file")
    parser.add_argument("--diff", required=True, help="Path to unified diff file")
    parser.add_argument("--guidelines", default="", help="Review guidelines text")
    parser.add_argument("--inference-url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args()

    with open(args.diff) as f:
        diff = f.read()

    comments = review_diff(
        diff,
        guidelines=args.guidelines,
        inference_url=args.inference_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    print(json.dumps([dataclasses.asdict(c) for c in comments], indent=2))


if __name__ == "__main__":
    _main()
