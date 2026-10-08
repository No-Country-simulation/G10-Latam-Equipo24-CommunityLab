"""Shared utilities for community topic normalization and ranking."""

from collections import Counter
import unicodedata


def _normalize_key(topic: str) -> str:
    """Return a lowercase, accent-free key used to group equivalent topics."""
    normalized = unicodedata.normalize("NFD", topic.lower())
    return "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def rank_topics(
    topics: list[str],
    top_n: int | None = None,
) -> list[tuple[str, int]]:
    """Normalize topics, rank them by frequency, and optionally limit the result.

    The returned labels preserve the first readable lowercase form seen for
    each normalized topic. If top_n is None, all topics are returned.
    """
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}

    for topic in topics:
        if not isinstance(topic, str) or not topic.strip():
            continue

        label = topic.strip()
        key = _normalize_key(label)

        if key not in labels:
            labels[key] = label.lower()

        counts[key] += 1

    return [
        (labels[key], count)
        for key, count in counts.most_common(top_n)
    ]
