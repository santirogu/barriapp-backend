"""Pure review logic (no DB): incremental rating recomputation."""


def recompute_rating(current_avg: float, current_count: int, new_stars: int) -> tuple[float, int]:
    """Fold a new rating into a running average. Returns (new_avg, new_count)."""
    count = current_count + 1
    avg = round((current_avg * current_count + new_stars) / count, 2)
    return avg, count
