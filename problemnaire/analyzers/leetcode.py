from dataclasses import dataclass, field
from problemnaire.fetchers.leetcode import LCProfile


COMFORTABLE_THRESHOLD = 10


@dataclass
class LCAnalysis:
    username: str
    easy_solved: int
    medium_solved: int
    hard_solved: int
    total_solved: int
    weak_topics: list[tuple[str, int]] = field(default_factory=list)  # (tag, count), < threshold
    top_topics: list[tuple[str, int]] = field(default_factory=list)   # strongest areas
    difficulty_score: str = ""


def analyze_lc(profile: LCProfile) -> LCAnalysis:
    # Use only what the platform actually returned — no hardcoded topic lists.
    # Weak = topics the user has touched but solved fewer than COMFORTABLE_THRESHOLD.
    weak = [
        (tag, count)
        for tag, count in profile.tag_counts.items()
        if 0 < count < COMFORTABLE_THRESHOLD
    ]
    weak.sort(key=lambda x: x[1])  # lowest first

    top = sorted(profile.tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    total = profile.total_solved
    if total < 50:
        score = "Beginner - focus on Easy problems first"
    elif profile.medium_solved < 30:
        score = "Developing - ramp up Medium problems"
    elif profile.hard_solved < 10:
        score = "Intermediate - start tackling Hard problems"
    else:
        score = "Advanced - focus on contest speed and patterns"

    return LCAnalysis(
        username=profile.username,
        easy_solved=profile.easy_solved,
        medium_solved=profile.medium_solved,
        hard_solved=profile.hard_solved,
        total_solved=total,
        weak_topics=weak,
        top_topics=top,
        difficulty_score=score,
    )
