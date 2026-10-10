import pytest
from src.utils.topics import rank_topics


def test_rank_topics_normalizes_case_and_accents():
    topics = ["Docker", "docker", "CONTRASEÑA", "contraseña"]

    assert rank_topics(topics) == [
        ("contraseña", 2),
        ("docker", 2),
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
        ("docker", 1),
        ("faq", 1),
        ("git", 1),
    ]


def test_rank_topics_ignores_empty_topics():
    topics = ["docker", "", "  ", "git"]

    assert rank_topics(topics) == [
        ("docker", 1),
        ("git", 1),
    ]


def test_rank_topics_breaks_frequency_ties_alphabetically():
    topics = ["git", "docker", "faq", "git", "docker", "faq"]

    assert rank_topics(topics) == [
        ("docker", 2),
        ("faq", 2),
        ("git", 2),
    ]


@pytest.mark.parametrize(
    ("singular", "plural"),
    [
        ("mensaje", "mensajes"),
        ("clave", "claves"),
        ("notificación", "notificaciones"),
        ("error", "errores"),
        ("papel", "papeles"),
        ("perfil", "perfiles"),
        ("jardín", "jardines"),
    ],
)
def test_rank_topics_groups_singular_and_plural(singular, plural):
    assert rank_topics([singular, plural]) == [(singular, 2)]


@pytest.mark.parametrize(
    ("singular", "plural"),
    [
        ("serie", "series"),
        ("servidor", "servidores"),
    ],
)
def test_rank_topics_handles_ambiguous_es_plurals(singular, plural):
    assert rank_topics([singular, plural]) == [(singular, 2)]


def test_rank_topics_plural_grouping_keeps_frequency_order():
    topics = [
        "perfil",
        "perfiles",
        "error",
        "errores",
        "errores",
        "docker",
    ]

    assert rank_topics(topics) == [
        ("error", 3),
        ("perfil", 2),
        ("docker", 1),
    ]


@pytest.mark.parametrize(
    "word",
    ["lunes", "martes", "miércoles", "jueves", "viernes",
     "crisis", "tesis", "dosis", "análisis", "paréntesis"],
)
def test_rank_topics_preserves_invariable_words(word):
    assert rank_topics([word]) == [(word, 1)]
