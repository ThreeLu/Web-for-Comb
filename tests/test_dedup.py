import json
import subprocess
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent / "pipeline"


def write_jsonl(path, papers):
    with open(path, "w") as f:
        for p in papers:
            f.write(json.dumps(p) + "\n")


def run_dedup(data_dir, date):
    return subprocess.run(
        [sys.executable, str(PIPELINE / "dedup.py"),
         "--date", date, "--data-dir", str(data_dir), "--history-days", "7"],
        capture_output=True, text=True,
    )


def test_removes_history_duplicates(tmp_path):
    write_jsonl(tmp_path / "2026-06-19.jsonl", [{"id": "1"}, {"id": "2"}])
    write_jsonl(tmp_path / "2026-06-20.jsonl", [{"id": "2"}, {"id": "3"}])
    run_dedup(tmp_path, "2026-06-20")
    remaining = [json.loads(l) for l in open(tmp_path / "2026-06-20.jsonl") if l.strip()]
    assert [p["id"] for p in remaining] == ["3"]


def test_deletes_file_when_all_duplicate(tmp_path):
    write_jsonl(tmp_path / "2026-06-19.jsonl", [{"id": "1"}])
    write_jsonl(tmp_path / "2026-06-20.jsonl", [{"id": "1"}])
    run_dedup(tmp_path, "2026-06-20")
    assert not (tmp_path / "2026-06-20.jsonl").exists()
