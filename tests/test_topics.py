from src.utils.topics import rank_topics


def test_rank_topics_normalizes_case_and_accents():
    topics = ["Docker", "docker", "CONTRASEÑA", "contraseña"]

    assert rank_topics(topics) == [
        ("docker", 2),
        ("contraseña", 2),
    ]


def test_rank_topics_orders_by_frequency():
    topics = ["git", "docker", "docker", "git", "docker", "faq"]

    assert rank_topics(topics) == [
        ("docker", 3),
        ("git", 2),
        ("faq", 1),
    ]


def test_rank_topics_respects_top_n():
    topics = ["git", "docker", "docker", "git", "docker", "faq"]

    assert rank_topics(topics, top_n=2) == [
        ("docker", 3),
        ("git", 2),
    ]


def test_rank_topics_without_limit_returns_all():
    topics = ["git", "docker", "faq"]

    assert rank_topics(topics, top_n=None) == [
        ("git", 1),
        ("docker", 1),
        ("faq", 1),
    ]


def test_rank_topics_ignores_empty_topics():
    topics = ["docker", "", "  ", "git"]

    assert rank_topics(topics) == [
        ("docker", 1),
        ("git", 1),
    ]
