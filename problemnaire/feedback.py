"""
Per-problem feedback sheet.

Source of truth : ~/.problemnaire/feedback_sheet.json
Human-readable  : ~/.problemnaire/feedback_sheet.md   (grouped by month)
Excel-compatible: ~/.problemnaire/feedback_sheet.csv

Schema for each entry:
{
  "date_solved"    : "YYYY-MM-DD",
  "platform"       : "cf" | "lc" | "cc",
  "problem_id"     : "4-A" | "two-sum",
  "title"          : "...",
  "tag"            : "...",
  "url"            : "...",
  "assigned_date"  : "YYYY-MM-DD",
  "difficulty_felt": "Easy" | "Medium" | "Hard" | "Very Hard",
  "needed_hint"    : true | false,
  "notes"          : "..."
}
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path


_DIR      = Path.home() / ".problemnaire"
_JSON     = _DIR / "feedback_sheet.json"
_MD       = _DIR / "feedback_sheet.md"
_CSV      = _DIR / "feedback_sheet.csv"

_DIFF_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}


def load() -> list[dict]:
    if not _JSON.exists():
        return []
    with open(_JSON, encoding="utf-8") as f:
        return json.load(f)


def save(entries: list[dict]) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    with open(_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)
    _write_md(entries)
    _write_csv(entries)


def add_entry(entries: list[dict], entry: dict) -> None:
    # Avoid duplicates: same problem_id + date_solved
    key = (entry["problem_id"], entry["date_solved"])
    entries[:] = [e for e in entries if (e["problem_id"], e["date_solved"]) != key]
    entries.append(entry)


def filter_by_period(entries: list[dict], period: str) -> list[dict]:
    """period: 'month' | 'quarter' | 'all'"""
    today = date.today()
    if period == "all":
        return entries
    if period == "quarter":
        cutoff = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    else:  # month
        cutoff = date(today.year, today.month, 1)
    return [e for e in entries if date.fromisoformat(e["date_solved"]) >= cutoff]


def to_markdown_content(entries: list[dict]) -> str:
    """Return just the table rows as a string (used for Claude prompt)."""
    if not entries:
        return "_No entries._"
    lines = ["| Date | Platform | Problem | Tag | Felt | Hint? | Notes |",
             "|------|----------|---------|-----|------|-------|-------|"]
    for e in sorted(entries, key=lambda x: x["date_solved"]):
        hint = "Yes" if e.get("needed_hint") else "No"
        link = f"[{e['title']}]({e['url']})"
        lines.append(
            f"| {e['date_solved']} | {e['platform'].upper()} | {link} "
            f"| {e.get('tag', '')} | {e.get('difficulty_felt', '')} | {hint} | {e.get('notes', '')} |"
        )
    return "\n".join(lines)


# ── internal writers ───────────────────────────────────────────────────────────

def _write_md(entries: list[dict]) -> None:
    lines = [
        "# Problemnaire Problem Feedback Sheet",
        f"_Last updated: {date.today()}_",
        "",
        "> Filter by month below. Each row = one solved problem.",
        "",
    ]

    # Group by YYYY-MM
    months: dict[str, list[dict]] = {}
    for e in sorted(entries, key=lambda x: x["date_solved"], reverse=True):
        key = e["date_solved"][:7]  # YYYY-MM
        months.setdefault(key, []).append(e)

    for month_key, month_entries in months.items():
        dt = datetime.strptime(month_key, "%Y-%m")
        lines.append(f"## {dt.strftime('%B %Y')}")
        lines.append("")
        lines.append("| Date | Platform | Problem | Tag | Felt | Hint? | Notes |")
        lines.append("|------|----------|---------|-----|------|-------|-------|")
        for e in month_entries:
            hint = "Yes" if e.get("needed_hint") else "No"
            link = f"[{e['title']}]({e['url']})"
            lines.append(
                f"| {e['date_solved']} | {e['platform'].upper()} | {link} "
                f"| {e.get('tag', '')} | {e.get('difficulty_felt', '')} | {hint} | {e.get('notes', '')} |"
            )
        lines.append("")

        # Mini summary for the month
        total = len(month_entries)
        hints = sum(1 for e in month_entries if e.get("needed_hint"))
        hard  = sum(1 for e in month_entries if e.get("difficulty_felt") in ("Hard", "Very Hard"))
        lines.append(f"_Total: {total} | Needed hint: {hints} | Found hard: {hard}_")
        lines.append("")

    with open(_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_csv(entries: list[dict]) -> None:
    fields = ["date_solved", "platform", "problem_id", "title", "tag",
              "difficulty_felt", "needed_hint", "notes", "url", "assigned_date"]
    with open(_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for e in sorted(entries, key=lambda x: x["date_solved"], reverse=True):
            writer.writerow(e)
