from collections import defaultdict
from dataclasses import dataclass, field
from problemnaire.fetchers.codeforces import CFProfile


# Typical tag distribution expected at each rating band (derived from CF community stats).
# These are the tags that become critical to master at each level.
RATING_BAND_IMPORTANT_TAGS: dict[tuple[int, int], list[str]] = {
    (0, 1199): ["implementation", "math", "greedy", "brute force", "constructive algorithms"],
    (1200, 1399): ["greedy", "math", "sorting", "binary search", "two pointers", "dp"],
    (1400, 1599): ["dp", "graphs", "dfs and similar", "trees", "binary search", "number theory"],
    (1600, 1799): ["dp", "graphs", "data structures", "trees", "math", "bitmasks", "shortest paths"],
    (1800, 1999): ["dp", "graphs", "data structures", "segment tree", "divide and conquer", "number theory"],
    (2000, 2199): ["dp", "graphs", "data structures", "segment tree", "flows", "strings", "fft"],
    (2200, 9999): ["dp", "graphs", "data structures", "flows", "strings", "fft", "hashing", "geometry"],
}

# Minimum solve count per tag to be considered "comfortable"
COMFORTABLE_THRESHOLD = 5


@dataclass
class TagStats:
    tag: str
    solved_below_target: int = 0   # solved in [current-200, current] band
    solved_at_target: int = 0      # solved in [current+1, current+200] band
    total_solved: int = 0


@dataclass
class CFAnalysis:
    handle: str
    current_rating: int
    target_rating: int
    solved_by_rating: dict[str, int] = field(default_factory=dict)   # band label → count
    tag_stats: list[TagStats] = field(default_factory=list)
    weak_tags: list[str] = field(default_factory=list)
    important_tags_for_target: list[str] = field(default_factory=list)
    total_solved: int = 0
    rated_solved: int = 0


def analyze_cf(profile: CFProfile, rating_boost: int = 200) -> CFAnalysis:
    current = profile.rating if profile.rating else 0
    target = current + rating_boost

    important = _get_important_tags(target)

    # Count solves per tag across all problems
    tag_totals: dict[str, int] = defaultdict(int)
    tag_at_target: dict[str, int] = defaultdict(int)
    tag_below_current: dict[str, int] = defaultdict(int)

    band_counts: dict[str, int] = defaultdict(int)
    rated_solved = 0

    for prob in profile.solved:
        r = prob["rating"]
        tags = prob["tags"]

        for tag in tags:
            tag_totals[tag] += 1

        if r is not None:
            rated_solved += 1
            band = _band_label(r)
            band_counts[band] += 1

            for tag in tags:
                if r <= current:
                    tag_below_current[tag] += 1
                if current < r <= target:
                    tag_at_target[tag] += 1

    # Build tag stats for important tags only
    tag_stats = []
    for tag in important:
        ts = TagStats(
            tag=tag,
            solved_below_target=tag_below_current.get(tag, 0),
            solved_at_target=tag_at_target.get(tag, 0),
            total_solved=tag_totals.get(tag, 0),
        )
        tag_stats.append(ts)

    # Weak tags: important for target, but solved fewer than threshold at or below target
    weak = [
        ts.tag for ts in tag_stats
        if ts.total_solved < COMFORTABLE_THRESHOLD
    ]

    return CFAnalysis(
        handle=profile.handle,
        current_rating=current,
        target_rating=target,
        solved_by_rating=dict(band_counts),
        tag_stats=tag_stats,
        weak_tags=weak,
        important_tags_for_target=important,
        total_solved=len(profile.solved),
        rated_solved=rated_solved,
    )


def _get_important_tags(target_rating: int) -> list[str]:
    for (lo, hi), tags in RATING_BAND_IMPORTANT_TAGS.items():
        if lo <= target_rating <= hi:
            return tags
    return RATING_BAND_IMPORTANT_TAGS[(2200, 9999)]


def _band_label(rating: int) -> str:
    bands = [800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 3500]
    for b in bands:
        if rating <= b:
            return str(b)
    return "3500+"
