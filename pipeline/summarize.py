#!/usr/bin/env python3
"""
AI summarization step — automated replacement for the old manual Claude/Codex
workflow.

Reads matched papers, calls an OpenAI-compatible chat API to produce a Chinese
structured summary for each, and writes data/{date}_ai_enhanced.jsonl with the
AI object nested under "AI" while preserving every original field.

Provider is fully configurable via environment variables (defaults to DeepSeek):

  LLM_API_KEY      required. Aliases accepted: DEEPSEEK_API_KEY, OPENAI_API_KEY
  LLM_BASE_URL     default: https://api.deepseek.com
  LLM_MODEL        default: deepseek-chat
  LLM_JSON_MODE    default: 1  (set to 0 for providers without JSON mode)
  LLM_MAX_WORKERS  default: 4

The step is resumable: papers already present with a complete "AI" object in the
output file are skipped, so a re-run only fills in the gaps.
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AI_FIELDS = ["tldr", "motivation", "method", "result", "conclusion", "future_work"]

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def get_api_key() -> str:
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(name)
        if val:
            return val
    print(
        "ERROR: no API key found. Set LLM_API_KEY (or DEEPSEEK_API_KEY / OPENAI_API_KEY).",
        file=sys.stderr,
    )
    sys.exit(2)


def build_client():
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "ERROR: the 'openai' package is required. Run `uv sync` or `pip install openai`.",
            file=sys.stderr,
        )
        sys.exit(2)

    # `or` (not the get default) so an empty CI variable falls back too.
    base_url = os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL
    return OpenAI(api_key=get_api_key(), base_url=base_url)


def load_jsonl(path: Path) -> list[dict]:
    papers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))
    return papers


def has_complete_ai(paper: dict) -> bool:
    ai = paper.get("AI")
    return isinstance(ai, dict) and all(ai.get(k) for k in AI_FIELDS)


def extract_json(text: str) -> dict:
    """Parse a JSON object out of a model response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the first {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON object found in response")


def format_paper(paper: dict) -> str:
    authors = paper.get("authors", [])
    if isinstance(authors, list):
        authors = ", ".join(authors)
    return (
        f"ID: {paper.get('id', '')}\n"
        f"Title: {paper.get('title', '')}\n"
        f"Authors: {authors}\n"
        f"Categories: {', '.join(paper.get('categories', []))}\n"
        f"Abstract: {paper.get('summary', '')}\n"
    )


def summarize_one(client, model, system_prompt, paper, json_mode, retries=3):
    """Return an AI dict for one paper, or raise after exhausting retries."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": format_paper(paper)},
    ]
    kwargs = {"model": model, "messages": messages, "temperature": 0.3}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            data = extract_json(content)
            return {k: str(data.get(k, "")).strip() for k in AI_FIELDS}
        except Exception as e:  # noqa: BLE001 — network/parse errors are all retryable
            last_err = e
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"failed after {retries} attempts: {last_err}")


def main():
    parser = argparse.ArgumentParser(description="AI-summarize matched papers")
    parser.add_argument("--input", required=True, help="Matched papers JSONL")
    parser.add_argument("--output", required=True, help="Output _ai_enhanced.jsonl")
    parser.add_argument(
        "--prompt",
        default=str(Path(__file__).parent / "prompt.md"),
        help="Path to the summarization prompt",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("LLM_MAX_WORKERS", "4")),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Cost guard: summarize at most this many papers (0 = no limit)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    papers = load_jsonl(input_path)
    if not papers:
        print("No papers to summarize.", file=sys.stderr)
        # Still emit an (empty) output file so downstream steps behave.
        output_path.write_text("")
        return

    # Resume: reuse AI summaries already written for these IDs.
    existing_ai: dict[str, dict] = {}
    if output_path.exists():
        for p in load_jsonl(output_path):
            if has_complete_ai(p):
                existing_ai[p.get("id", "")] = p["AI"]

    system_prompt = Path(args.prompt).read_text()
    model = os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    json_mode = (os.environ.get("LLM_JSON_MODE") or "1") != "0"

    # Cost guard: only the first N papers are eligible for summarization.
    # Any beyond the cap are written through without an AI object (and thus
    # skipped by the markdown/RSS steps).
    eligible = papers[: args.limit] if args.limit and args.limit > 0 else papers
    if len(eligible) < len(papers):
        print(
            f"NOTE: --limit {args.limit} — only summarizing {len(eligible)} of "
            f"{len(papers)} papers (cost guard).",
            file=sys.stderr,
        )
    todo = [p for p in eligible if p.get("id", "") not in existing_ai]
    print(
        f"Summarizing {len(todo)}/{len(papers)} papers "
        f"({len(existing_ai)} reused) with model '{model}'...",
        file=sys.stderr,
    )

    client = build_client() if todo else None
    results: dict[str, dict] = dict(existing_ai)
    failures = 0

    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(summarize_one, client, model, system_prompt, p, json_mode): p
                for p in todo
            }
            for fut in as_completed(futures):
                paper = futures[fut]
                pid = paper.get("id", "")
                try:
                    results[pid] = fut.result()
                    print(f"  ✓ {pid}", file=sys.stderr)
                except Exception as e:  # noqa: BLE001
                    failures += 1
                    print(f"  ✗ {pid}: {e}", file=sys.stderr)

    # Write output in the original input order, preserving all fields.
    written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for paper in papers:
            pid = paper.get("id", "")
            if pid in results:
                paper["AI"] = results[pid]
                written += 1
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(f"Wrote {written}/{len(papers)} papers with AI summaries to {output_path}", file=sys.stderr)
    if failures:
        print(f"WARNING: {failures} papers failed to summarize.", file=sys.stderr)
        # Non-zero exit if everything failed, so CI surfaces a total outage.
        if written == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
