import httpx
from dataclasses import dataclass, field


LC_GRAPHQL = "https://leetcode.com/graphql"

_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
}

_QUERY_PROFILE = """
query userProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStats: submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    tagProblemCounts {
      advanced {
        tagName
        problemsSolved
      }
      intermediate {
        tagName
        problemsSolved
      }
      fundamental {
        tagName
        problemsSolved
      }
    }
  }
}
"""


@dataclass
class LCProfile:
    username: str
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    total_solved: int = 0
    tag_counts: dict[str, int] = field(default_factory=dict)  # tagName → count


def fetch_lc_profile(username: str) -> LCProfile:
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            LC_GRAPHQL,
            headers=_HEADERS,
            json={"query": _QUERY_PROFILE, "variables": {"username": username}},
        )
    resp.raise_for_status()
    data = resp.json()

    user = data.get("data", {}).get("matchedUser")
    if not user:
        raise RuntimeError(f"LeetCode user '{username}' not found or profile is private.")

    easy = medium = hard = 0
    for entry in user.get("submitStats", {}).get("acSubmissionNum", []):
        diff = entry["difficulty"]
        count = entry["count"]
        if diff == "Easy":
            easy = count
        elif diff == "Medium":
            medium = count
        elif diff == "Hard":
            hard = count

    tag_counts: dict[str, int] = {}
    for group in ("fundamental", "intermediate", "advanced"):
        for item in user.get("tagProblemCounts", {}).get(group, []):
            tag_counts[item["tagName"]] = item["problemsSolved"]

    return LCProfile(
        username=username,
        easy_solved=easy,
        medium_solved=medium,
        hard_solved=hard,
        total_solved=easy + medium + hard,
        tag_counts=tag_counts,
    )
