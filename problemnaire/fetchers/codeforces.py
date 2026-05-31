import requests
from dataclasses import dataclass, field
from typing import Optional


CF_API = "https://codeforces.com/api"


@dataclass
class CFProfile:
    handle: str
    rating: int
    max_rating: int
    rank: str
    solved: list[dict] = field(default_factory=list)  # accepted submissions deduped by problem


def fetch_cf_profile(handle: str) -> CFProfile:
    info = _get(f"{CF_API}/user.info", params={"handles": handle})["result"][0]
    rating = info.get("rating", 0)
    max_rating = info.get("maxRating", 0)
    rank = info.get("rank", "unrated")

    subs = _get(f"{CF_API}/user.status", params={"handle": handle, "from": 1, "count": 10000})
    solved = _dedup_accepted(subs["result"])

    return CFProfile(handle=handle, rating=rating, max_rating=max_rating, rank=rank, solved=solved)


def _dedup_accepted(submissions: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result = []
    for sub in submissions:
        if sub.get("verdict") != "OK":
            continue
        prob = sub.get("problem", {})
        key = (prob.get("contestId"), prob.get("index"))
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "name": prob.get("name", ""),
            "rating": prob.get("rating"),        # may be None if unrated
            "tags": prob.get("tags", []),
            "contestId": prob.get("contestId"),
            "index": prob.get("index"),
        })
    return result


def _get(url: str, params: Optional[dict] = None) -> dict:
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"Codeforces API error: {data.get('comment', 'unknown error')}")
    return data
