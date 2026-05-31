import re
import requests
from dataclasses import dataclass


@dataclass
class CCProfile:
    username: str
    rating: int = 0
    highest_rating: int = 0
    fully_solved: int = 0


def fetch_cc_profile(username: str) -> CCProfile:
    url = f"https://www.codechef.com/users/{username}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Problemnaire/0.1)"}
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 404:
        raise RuntimeError(f"CodeChef user '{username}' not found.")
    resp.raise_for_status()

    text = resp.text

    # Ratings are embedded as "rating":"XXXX" entries in the date_versus_rating JSON blob.
    # The last entry is the current rating; the max across all entries is the highest.
    ratings = [int(x) for x in re.findall(r'"rating":"(\d+)"', text)]
    current = ratings[-1] if ratings else 0
    highest = max(ratings) if ratings else 0

    m = re.search(r"Problems Solved:\s*(\d+)", text)
    fully_solved = int(m.group(1)) if m else 0

    return CCProfile(
        username=username,
        rating=current,
        highest_rating=highest,
        fully_solved=fully_solved,
    )
