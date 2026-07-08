import json

import pytest

import summarize as S


def test_extract_json_plain():
    assert S.extract_json('{"tldr":"a"}')["tldr"] == "a"


def test_extract_json_fenced():
    assert S.extract_json('```json\n{"tldr":"b"}\n```')["tldr"] == "b"


def test_extract_json_embedded():
    assert S.extract_json('noise {"tldr":"c"} tail')["tldr"] == "c"


def test_extract_json_invalid():
    with pytest.raises((ValueError, json.JSONDecodeError)):
        S.extract_json("not json at all")


def test_has_complete_ai():
    good = {"AI": {k: "x" for k in S.AI_FIELDS}}
    assert S.has_complete_ai(good)
    missing = {"AI": {k: "x" for k in S.AI_FIELDS[:-1]}}
    assert not S.has_complete_ai(missing)
    assert not S.has_complete_ai({})


def _run_main(monkeypatch, in_path, out_path, extra_argv=None):
    monkeypatch.setattr(S, "build_client", lambda: object())
    monkeypatch.setattr(
        S, "summarize_one",
        lambda client, model, prompt, paper, json_mode, retries=3: {
            k: f"{k}-{paper['id']}" for k in S.AI_FIELDS
        },
    )
    argv = ["summarize.py", "--input", str(in_path), "--output", str(out_path)]
    if extra_argv:
        argv += extra_argv
    monkeypatch.setattr("sys.argv", argv)
    S.main()


def test_merge_preserves_fields_and_adds_ai(tmp_path, monkeypatch):
    inp = tmp_path / "in.jsonl"
    with open(inp, "w") as f:
        f.write(json.dumps({"id": "1", "title": "T", "matched": True,
                            "match_reasons": {"keywords": ["k"], "authors": []}}) + "\n")
    out = tmp_path / "out.jsonl"
    _run_main(monkeypatch, inp, out)
    row = json.loads(open(out).readline())
    assert row["title"] == "T"
    assert row["matched"] is True
    assert row["match_reasons"]["keywords"] == ["k"]
    assert set(row["AI"]) == set(S.AI_FIELDS)


def test_limit_caps_summaries(tmp_path, monkeypatch):
    inp = tmp_path / "in.jsonl"
    with open(inp, "w") as f:
        for i in range(5):
            f.write(json.dumps({"id": str(i), "title": f"T{i}"}) + "\n")
    out = tmp_path / "out.jsonl"
    _run_main(monkeypatch, inp, out, extra_argv=["--limit", "2"])
    rows = [json.loads(l) for l in open(out) if l.strip()]
    assert len(rows) == 5                       # all rows written
    with_ai = [r for r in rows if r.get("AI")]
    assert len(with_ai) == 2                     # only first 2 summarized
