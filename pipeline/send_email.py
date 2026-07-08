#!/usr/bin/env python3
"""
Optional daily email digest of matched papers.

Fully opt-in: if SMTP_HOST is not set, this exits quietly (0) so the pipeline
runs fine without email configured. To enable, set these env vars (as GitHub
Secrets for CI):

  SMTP_HOST         e.g. smtp.gmail.com
  SMTP_PORT         default 587 (STARTTLS)
  SMTP_USER         login username
  SMTP_PASSWORD     login password / app password
  EMAIL_FROM        default: SMTP_USER
  EMAIL_TO          comma-separated recipients (default: EMAIL_FROM)
"""

import argparse
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from pathlib import Path


def load_matched(path: Path) -> list[dict]:
    papers = []
    if not path.exists():
        return papers
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    papers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return [p for p in papers if p.get("AI")]


def render_html(papers: list[dict], date: str) -> str:
    rows = []
    for i, p in enumerate(papers, 1):
        pid = p.get("id", "")
        link = p.get("abs") or f"https://arxiv.org/abs/{pid}"
        tldr = escape((p.get("AI") or {}).get("tldr", ""))
        authors = p.get("authors", [])
        authors = escape(", ".join(authors) if isinstance(authors, list) else str(authors))
        reasons = p.get("match_reasons") or {}
        why = ", ".join(list(reasons.get("keywords", [])) + [f"@{a}" for a in reasons.get("authors", [])])
        why_html = f'<div style="color:#888;font-size:12px">命中: {escape(why)}</div>' if why else ""
        rows.append(
            f'<div style="margin:0 0 18px">'
            f'<a href="{escape(link)}" style="font-weight:600;color:#2b6cb0;text-decoration:none">{i}. {escape(p.get("title",""))}</a>'
            f'<div style="color:#666;font-size:12px;margin:2px 0">{authors}</div>'
            f'<div style="margin:4px 0">{tldr}</div>'
            f"{why_html}</div>"
        )
    return (
        f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:720px;margin:auto">'
        f"<h2>Comb-Search · {escape(date)} · {len(papers)} 篇</h2>"
        + "".join(rows)
        + '<hr><div style="color:#aaa;font-size:12px">'
        '<a href="https://threelu.github.io/Web-for-Comb/">查看网站</a></div></div>'
    )


def main():
    parser = argparse.ArgumentParser(description="Send daily email digest")
    parser.add_argument("--data", required=True, help="Path to {date}_ai_enhanced.jsonl")
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    host = os.environ.get("SMTP_HOST")
    if not host:
        print("SMTP_HOST not set — skipping email digest.", file=sys.stderr)
        return

    papers = load_matched(Path(args.data))
    if not papers:
        print("No papers to email.", file=sys.stderr)
        return

    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    port = int(os.environ.get("SMTP_PORT") or "587")
    sender = os.environ.get("EMAIL_FROM") or user
    recipients = [r.strip() for r in (os.environ.get("EMAIL_TO") or sender).split(",") if r.strip()]

    msg = EmailMessage()
    msg["Subject"] = f"Comb-Search {args.date} — {len(papers)} 篇匹配论文"
    msg["From"] = formataddr(("Comb-Search", sender))
    msg["To"] = ", ".join(recipients)
    msg.set_content(f"{len(papers)} matched papers for {args.date}. View: https://threelu.github.io/Web-for-Comb/")
    msg.add_alternative(render_html(papers, args.date), subtype="html")

    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if user:
            s.login(user, password)
        s.send_message(msg)
    print(f"Sent digest to {', '.join(recipients)}", file=sys.stderr)


if __name__ == "__main__":
    main()
