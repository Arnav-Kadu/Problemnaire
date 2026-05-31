"""
Handle ownership verification and problem-solved verification.

Handle verification
  CF : CLI assigns a problem → user submits it → we check their LATEST AC is that problem.
  LC : same idea, checked against recentAcSubmissionList[0].
  CC : no public submissions API; we just confirm the profile page is reachable.

Problem verification (Claude-assigned problems)
  CF : problem must appear in submissions with AC verdict AND submission date >= assigned_date.
  LC : same, using the timestamp field from recentAcSubmissionList.
"""

import requests
import httpx
from datetime import date, datetime


CF_VERIFY_CONTEST = "4"
CF_VERIFY_INDEX   = "A"
CF_VERIFY_URL     = "https://codeforces.com/problemset/problem/4/A"
CF_API            = "https://codeforces.com/api"

LC_VERIFY_SLUG    = "two-sum"
LC_VERIFY_URL     = "https://leetcode.com/problems/two-sum/"
LC_GRAPHQL        = "https://leetcode.com/graphql"


# ── CF ─────────────────────────────────────────────────────────────────────────

def is_cf_handle_verified(handle: str) -> bool:
    """
    The user's most recent AC submission must be CF 4A (Watermelon).
    Prevents reuse of any handle that has already solved 4A in the past.
    """
    subs = _cf_submissions(handle, count=10)
    for sub in subs:
        if sub.get("verdict") == "OK":
            prob = sub.get("problem", {})
            return (
                str(prob.get("contestId")) == CF_VERIFY_CONTEST
                and prob.get("index") == CF_VERIFY_INDEX
            )
    return False


def is_cf_problem_solved(handle: str, contest_id: str, index: str, since_date: str) -> bool:
    """
    Returns True if the user AC'd this problem on or after since_date.
    Checks the submission timestamp so they can't claim credit for a pre-existing solve.
    """
    since = date.fromisoformat(since_date)
    subs = _cf_submissions(handle, count=2000)
    for sub in subs:
        if sub.get("verdict") != "OK":
            continue
        prob = sub.get("problem", {})
        if str(prob.get("contestId")) == str(contest_id) and prob.get("index") == index:
            sub_date = datetime.fromtimestamp(sub["creationTimeSeconds"]).date()
            if sub_date >= since:
                return True
    return False


def _cf_submissions(handle: str, count: int) -> list:
    try:
        resp = requests.get(
            f"{CF_API}/user.status",
            params={"handle": handle, "from": 1, "count": count},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK":
            return data["result"]
    except Exception:
        pass
    return []


# ── LC ─────────────────────────────────────────────────────────────────────────

def is_lc_handle_verified(username: str) -> bool:
    """
    The user's most recent AC on LeetCode must be Two Sum.
    """
    subs = _lc_recent_ac(username, limit=5)
    return bool(subs) and subs[0]["titleSlug"] == LC_VERIFY_SLUG


def is_lc_problem_solved(username: str, slug: str, since_date: str) -> bool:
    """
    Returns True if the slug appears in recent ACs with a timestamp >= since_date.
    """
    since = date.fromisoformat(since_date)
    subs = _lc_recent_ac(username, limit=100)
    for sub in subs:
        if sub["titleSlug"] == slug:
            sub_date = datetime.fromtimestamp(int(sub["timestamp"])).date()
            if sub_date >= since:
                return True
    return False


def _lc_recent_ac(username: str, limit: int) -> list:
    query = """
    query recentAC($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        titleSlug
        timestamp
      }
    }
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                LC_GRAPHQL,
                headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
                json={"query": query, "variables": {"username": username, "limit": limit}},
            )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("recentAcSubmissionList", [])
    except Exception:
        return []


# ── CC ─────────────────────────────────────────────────────────────────────────

def is_cc_handle_reachable(username: str) -> bool:
    try:
        resp = requests.get(
            f"https://www.codechef.com/users/{username}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
