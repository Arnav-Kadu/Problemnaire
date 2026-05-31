"""
Manages ~/.problemnaire/progress.json  (machine-readable source of truth)
and auto-generates ~/.problemnaire/progress.md  (human-readable report).

Schema of progress.json:
{
  "last_session_summary": "",
  "pending_problems": [...],
  "sessions": [...],
  "feedback_log": [          # standalone feedback entries (any time, not just analyze)
    {
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "worked_on": "...",
      "what_clicked": "...",
      "what_confused": "...",
      "next_goal": "...",
      "mood": "Great" | "Good" | "Okay" | "Struggling"
    }
  ]
}
"""

import json
from datetime import date, datetime
from pathlib import Path


_DIR       = Path.home() / ".problemnaire"
_JSON_FILE = _DIR / "progress.json"
_MD_FILE   = _DIR / "progress.md"

_MOOD_ICON = {
    "Great":      "[+]",
    "Good":       "[~]",
    "Okay":       "[-]",
    "Struggling": "[!]",
}


def load() -> dict:
    if not _JSON_FILE.exists():
        return {"last_session_summary": "", "pending_problems": [], "sessions": [], "feedback_log": []}
    data = json.load(open(_JSON_FILE, encoding="utf-8"))
    data.setdefault("feedback_log", [])
    return data


def save(data: dict) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    with open(_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    _write_md(data)


def add_feedback_entry(data: dict, *, worked_on: str, what_clicked: str,
                       what_confused: str, next_goal: str, mood: str) -> None:
    now = datetime.now()
    data.setdefault("feedback_log", []).append({
        "date":          str(now.date()),
        "time":          now.strftime("%H:%M"),
        "mood":          mood,
        "worked_on":     worked_on,
        "what_clicked":  what_clicked,
        "what_confused": what_confused,
        "next_goal":     next_goal,
    })


def add_session(data: dict, *, cf_rating: int, lc_solved: int, cc_rating: int,
                problems_assigned: list, problems_solved: list, feedback: str,
                summary: str) -> None:
    data["last_session_summary"] = summary
    data["sessions"].append({
        "date": str(date.today()),
        "cf_rating": cf_rating,
        "lc_solved": lc_solved,
        "cc_rating": cc_rating,
        "problems_assigned": problems_assigned,
        "problems_solved": problems_solved,
        "feedback": feedback,
    })
    for p in problems_assigned:
        p["verified_solved"] = False
        p["assigned_date"] = str(date.today())
        data["pending_problems"].append(p)
    solved_ids = set(problems_solved)
    data["pending_problems"] = [
        p for p in data["pending_problems"] if p["id"] not in solved_ids
    ]


def _write_md(data: dict) -> None:
    lines = ["# Problemnaire Progress Report", f"_Last updated: {date.today()}_", ""]

    # ── Pending problems ───────────────────────────────────────────────────────
    lines += ["## Pending Problems", ""]
    pending = data.get("pending_problems", [])
    if pending:
        lines.append("| Platform | Problem | Tag | Assigned |")
        lines.append("|----------|---------|-----|----------|")
        for p in pending:
            lines.append(
                f"| {p['platform'].upper()} | [{p['title']}]({p['url']}) "
                f"| {p['tag']} | {p['assigned_date']} |"
            )
    else:
        lines.append("_No pending problems._")
    lines.append("")

    # ── Feedback log (standalone entries) ─────────────────────────────────────
    feedback_log = data.get("feedback_log", [])
    if feedback_log:
        lines += ["## Feedback Log", ""]

        # Group by month (YYYY-MM)
        months: dict[str, list] = {}
        for entry in feedback_log:
            key = entry["date"][:7]
            months.setdefault(key, []).append(entry)

        for month_key in sorted(months.keys(), reverse=True):
            month_dt = datetime.strptime(month_key, "%Y-%m")
            lines.append(f"### {month_dt.strftime('%B %Y')}")
            lines.append("")
            for e in reversed(months[month_key]):
                icon = _MOOD_ICON.get(e.get("mood", ""), "[ ]")
                lines.append(f"#### {e['date']} {e['time']}  {icon} {e.get('mood', '')}")
                if e.get("worked_on"):
                    lines.append(f"- **Worked on:** {e['worked_on']}")
                if e.get("what_clicked"):
                    lines.append(f"- **Clicked:** {e['what_clicked']}")
                if e.get("what_confused"):
                    lines.append(f"- **Confused by:** {e['what_confused']}")
                if e.get("next_goal"):
                    lines.append(f"- **Next goal:** {e['next_goal']}")
                lines.append("")

    # ── Session history ────────────────────────────────────────────────────────
    lines += ["## Session History", ""]
    for s in reversed(data.get("sessions", [])):
        lines.append(f"### {s['date']}")
        lines.append(
            f"- CF: {s['cf_rating']}  |  LC solved: {s['lc_solved']}  |  CC: {s['cc_rating']}"
        )
        if s.get("problems_assigned"):
            assigned = ", ".join(p["title"] for p in s["problems_assigned"])
            lines.append(f"- Assigned: {assigned}")
        if s.get("problems_solved"):
            lines.append(f"- Solved: {', '.join(s['problems_solved'])}")
        if s.get("feedback"):
            lines.append(f"- Notes: _{s['feedback']}_")
        lines.append("")

    # ── Last Claude summary ────────────────────────────────────────────────────
    if data.get("last_session_summary"):
        lines += ["## Last Session Summary", "", data["last_session_summary"], ""]

    with open(_MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
