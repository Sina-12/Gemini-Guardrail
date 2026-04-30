#!/usr/bin/env python3
"""Simple one-shot tester for POST /guardrail/phase1.

Usage:
  python test_api.py 0
  python test_api.py 12 --base-url http://127.0.0.1:8000 --max-iters 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests


TEXT_COLUMN_CANDIDATES = [
    "source_text",
    "source",
    "original_text",
    "text",
    "post_text",
    "thread_text",
    "body",
    "content",
]
SUMMARY_COLUMN_CANDIDATES = [
    "summary",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test the dynamic guardrail endpoint with one dataset row.")
    parser.add_argument(
        "row_index",
        nargs="?",
        default=0,
        type=int,
        help="0-based row index from data/full_annotations_with_source_text.csv (default: 0)",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--max-iters", type=int, default=3, help="Max correction iterations.")
    parser.add_argument("--min-support-ratio", type=float, default=0.8, help="Acceptance threshold for support ratio.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help=(
            "Client timeout (seconds) for POST /guardrail/phase1. "
            "Use >= 3600 if the guardrail runs many claim checks through local Ollama."
        ),
    )
    return parser


def _resolve_text_column(df: pd.DataFrame) -> str:
    column_map = {c.lower().strip(): c for c in df.columns}
    text_col = None

    for candidate in TEXT_COLUMN_CANDIDATES:
        if candidate in column_map:
            text_col = column_map[candidate]
            break

    if text_col is None:
        fuzzy_cols = []
        for original in df.columns:
            normalized = original.lower().strip()
            if any(k in normalized for k in ("source", "text", "body", "content")):
                fuzzy_cols.append(original)
        if fuzzy_cols:
            text_col = fuzzy_cols[0]

    if text_col is None:
        raise ValueError(
            "Could not find a usable source text column. "
            f"Available columns: {list(df.columns)}"
        )
    return text_col


def _resolve_summary_column(df: pd.DataFrame) -> str:
    column_map = {c.lower().strip(): c for c in df.columns}
    for candidate in SUMMARY_COLUMN_CANDIDATES:
        if candidate in column_map:
            return column_map[candidate]

    for original in df.columns:
        if "summary" in original.lower().strip():
            return original

    raise ValueError(
        "Could not find a usable summary column. "
        f"Available columns: {list(df.columns)}"
    )


def load_guardrail_inputs(repo_root: Path, row_index: int) -> tuple[str, str]:
    data_path = repo_root / "data" / "full_annotations_with_source_text.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path, encoding="latin1")
    if df.empty:
        raise ValueError(f"No rows found in {data_path}")

    text_col = _resolve_text_column(df)
    summary_col = _resolve_summary_column(df)

    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"row_index {row_index} out of range. Valid range: 0..{len(df)-1}")

    source_text = str(df.iloc[row_index][text_col]).strip()
    summary_text = str(df.iloc[row_index][summary_col]).strip()

    if source_text.lower() in {"nan", "none"}:
        source_text = ""
    if summary_text.lower() in {"nan", "none"}:
        summary_text = ""

    if not source_text:
        raise ValueError(
            f"Row {row_index} has empty source text in column '{text_col}'. "
            "Pick a row with non-empty source text."
        )
    if not summary_text:
        raise ValueError(
            f"Row {row_index} has empty summary in column '{summary_col}'. "
            "Pick a row with non-empty summary."
        )

    return source_text, summary_text


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    source_text, summary_text = load_guardrail_inputs(repo_root, args.row_index)

    payload = {
        "source_text": source_text,
        "summary": summary_text,
        "max_iters": args.max_iters,
        "min_support_ratio": args.min_support_ratio,
    }
    url = f"{args.base_url.rstrip('/')}/guardrail/phase1"
    response = requests.post(url, json=payload, timeout=args.timeout)
    if not response.ok:
        detail = response.text
        try:
            detail = json.dumps(response.json(), indent=2, ensure_ascii=True)
        except Exception:
            pass
        raise RuntimeError(f"Request failed: HTTP {response.status_code}\n{detail}")

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
