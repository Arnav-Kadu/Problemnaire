"""
Token-efficient Claude integration.

Strategy to avoid burning tokens:
- Build a compact plain-text context (stats summary, NOT raw submissions).
- Include only the stored last_session_summary (<=150 words), not full history.
- Ask Claude to return strict JSON so we can parse it reliably.
- At the end of each session, ask Claude for a <=100-word summary to store,
  replacing the previous one. Full history lives in progress.json locally.
"""

import json
import anthropic

MODEL_FAST  = "claude-haiku-4-5-20251001"   # used for regular analyze (cheap)
MODEL_DEEP  = "claude-sonnet-4-6"           # used for review command (higher quality)
MODEL = MODEL_FAST  # default alias kept for existing callers


def get_recommendations(
    *,
    cf_analysis,       # CFAnalysis | None
    lc_analysis,       # LCAnalysis | None
    cc_analysis,       # CCAnalysis | None
    last_summary: str,
    last_feedback: str,
    api_key: str,
) -> dict:
    """
    Returns:
    {
      "cf_problems": [{"contest_id": "4", "index": "A", "title": "...", "rating": 800, "reason": "..."}],
      "lc_problems": [{"slug": "...", "title": "...", "difficulty": "Medium", "reason": "..."}],
      "advice": "...",
      "session_summary": "..."   # <=100 words, stored for next run
    }
    """
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(cf_analysis, lc_analysis, cc_analysis, last_summary, last_feedback)

    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    return _parse(raw)


def build_session_summary(feedback: str, problems_solved: list[str], api_key: str) -> str:
    """Ask Claude to write a <=100-word summary of this session to store for next time."""
    client = anthropic.Anthropic(api_key=api_key)
    solved_str = ", ".join(problems_solved) if problems_solved else "none"
    prompt = (
        f"Write a 1-2 sentence (max 100 words) summary of this competitive programming study session.\n"
        f"Problems solved: {solved_str}\n"
        f"User feedback: {feedback or 'no feedback'}\n"
        f"Be factual and concise. This will be read by an AI coach next session."
    )
    msg = client.messages.create(
        model=MODEL,
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def deep_analysis(*, feedback_md: str, period: str, api_key: str) -> str:
    """
    Feed the full feedback sheet to Claude Sonnet for a deep pattern analysis.

    This is intentionally expensive — it sends the entire feedback history
    and uses the Sonnet model for quality. Users are warned before calling this.
    """
    client = anthropic.Anthropic(api_key=api_key)

    period_label = {"month": "this month", "quarter": "this quarter", "all": "all time"}.get(period, period)

    prompt = (
        f"You are an expert competitive programming coach performing a deep review "
        f"of a student's practice history ({period_label}).\n\n"
        f"Below is their complete problem feedback sheet. Each row is a problem they solved, "
        f"with how hard it felt, whether they needed a hint, and their personal notes.\n\n"
        f"=== FEEDBACK SHEET ===\n"
        f"{feedback_md}\n"
        f"======================\n\n"
        f"Provide a thorough analysis covering:\n"
        f"1. **Pattern analysis** - what types of problems are consistently hard? "
        f"Any tags/topics where hints are frequently needed?\n"
        f"2. **Improvement trends** - what is getting easier over time?\n"
        f"3. **Specific weaknesses** - based on notes, what conceptual gaps keep appearing?\n"
        f"4. **Recommended focus areas** - 3-5 specific topics to drill, with a concrete reason for each\n"
        f"5. **Problem suggestions** - 2-3 specific CF or LC problems (real ones with IDs/slugs) "
        f"that directly address the identified gaps\n"
        f"6. **One motivational observation** - something genuinely positive from their history\n\n"
        f"Be specific and reference actual problems from their feedback. Be direct and actionable."
    )

    msg = client.messages.create(
        model=MODEL_DEEP,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── private ────────────────────────────────────────────────────────────────────

def _build_prompt(cf, lc, cc, last_summary, last_feedback) -> str:
    parts = ["You are a competitive programming coach. Analyze this student and assign specific practice problems.\n"]

    if cf:
        weak_tags = ", ".join(cf.weak_tags) if cf.weak_tags else "none"
        strong = sorted(cf.tag_stats, key=lambda x: x.total_solved, reverse=True)[:3]
        strong_str = ", ".join(f"{t.tag}({t.total_solved})" for t in strong)
        parts.append(
            f"CODEFORCES: handle={cf.handle} | rating={cf.current_rating} | target={cf.target_rating}\n"
            f"  Total solved: {cf.total_solved} | Rated: {cf.rated_solved}\n"
            f"  Weak tags (need work): {weak_tags}\n"
            f"  Strong tags: {strong_str}\n"
        )

    if lc:
        weak_str = ", ".join(f"{t}({c})" for t, c in lc.weak_topics[:5])
        top_str  = ", ".join(f"{t}({c})" for t, c in lc.top_topics[:3])
        parts.append(
            f"LEETCODE: handle={lc.username} | solved={lc.total_solved} "
            f"({lc.easy_solved}E/{lc.medium_solved}M/{lc.hard_solved}H)\n"
            f"  Weak topics: {weak_str}\n"
            f"  Strong topics: {top_str}\n"
            f"  Assessment: {lc.difficulty_score}\n"
        )

    if cc:
        parts.append(
            f"CODECHEF: handle={cc.username} | rating={cc.current_rating} | "
            f"need +{cc.points_to_next} for {cc.next_band}\n"
        )

    if last_summary:
        parts.append(f"LAST SESSION SUMMARY: {last_summary}\n")

    if last_feedback:
        parts.append(f"USER FEEDBACK FROM LAST SESSION: {last_feedback}\n")

    parts.append(
        "\nAssign 2-3 Codeforces problems and 2-3 LeetCode problems targeted at the student's weak areas.\n"
        "Choose real problems that actually exist. For CF, use real contest IDs and indices.\n"
        "For LC, use real problem slugs (the part after /problems/ in the URL).\n"
        "Also write 1-2 sentences of personalised advice based on their profile and feedback.\n"
        "Finally, write a session_summary (max 100 words) for storage.\n\n"
        "Respond ONLY with valid JSON in this exact format:\n"
        "{\n"
        '  "cf_problems": [\n'
        '    {"contest_id": "4", "index": "A", "title": "Watermelon", "rating": 800, "reason": "..."}\n'
        "  ],\n"
        '  "lc_problems": [\n'
        '    {"slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium", "reason": "..."}\n'
        "  ],\n"
        '  "advice": "...",\n'
        '  "session_summary": "..."\n'
        "}"
    )
    return "\n".join(parts)


def _parse(raw: str) -> dict:
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Graceful fallback — return empty structure so the CLI doesn't crash
        return {
            "cf_problems": [],
            "lc_problems": [],
            "advice": raw,
            "session_summary": "",
        }
