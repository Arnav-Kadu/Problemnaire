from dataclasses import dataclass
from problemnaire.fetchers.codechef import CCProfile


# CodeChef rating bands → star label
STAR_BANDS = [
    (0, 1399, "1*", "Beginner"),
    (1400, 1599, "2*", "Beginner-Intermediate"),
    (1600, 1799, "3*", "Intermediate"),
    (1800, 1999, "4*", "Intermediate-Advanced"),
    (2000, 2199, "5*", "Advanced"),
    (2200, 2499, "6*", "Expert"),
    (2500, 9999, "7*", "Expert+"),
]


@dataclass
class CCAnalysis:
    username: str
    current_rating: int
    highest_rating: int
    current_band: str
    next_band: str
    points_to_next: int
    fully_solved: int
    advice: str


def analyze_cc(profile: CCProfile) -> CCAnalysis:
    current = profile.rating
    current_band, next_band, points_to_next = _get_band_info(current)

    if current < 1400:
        advice = "Focus on Div 3 & Div 4 contests. Solve beginner implementation problems."
    elif current < 1600:
        advice = "Practice greedy, basic DP, and sorting problems in Div 3 contests."
    elif current < 1800:
        advice = "Work on graphs (BFS/DFS), binary search, and prefix sums."
    elif current < 2000:
        advice = "Tackle advanced DP, segment trees, and Div 2 contest problems."
    else:
        advice = "Focus on Div 1 problems, advanced data structures, and competitive techniques."

    return CCAnalysis(
        username=profile.username,
        current_rating=current,
        highest_rating=profile.highest_rating,
        current_band=current_band,
        next_band=next_band,
        points_to_next=points_to_next,
        fully_solved=profile.fully_solved,
        advice=advice,
    )


def _get_band_info(rating: int) -> tuple[str, str, int]:
    for i, (lo, hi, stars, label) in enumerate(STAR_BANDS):
        if lo <= rating <= hi:
            current_band = f"{stars} {label} ({lo}-{hi})"
            if i + 1 < len(STAR_BANDS):
                nlo, _, nstars, nlabel = STAR_BANDS[i + 1]
                next_band = f"{nstars} {nlabel}"
                points = nlo - rating
            else:
                next_band = "Max tier reached"
                points = 0
            return current_band, next_band, points
    return "Unknown", "Unknown", 0
