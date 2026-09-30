import pytest

from src.decisions.recurring_topics import RecurringTopicsDetector


def test_detects_recurring_topic():
    detector = RecurringTopicsDetector()

    messages = [
        "¿Cómo puedo cambiar mi contraseña?",
        "¿Dónde puedo cambiar la contraseña?",
        "¿Cómo actualizo mi perfil?",
    ]

    results = detector.detect(messages)

    assert len(results) == 1
    assert results[0].topic == "contraseña"
    assert results[0].count == 2


def test_ignores_topics_with_one_occurrence():
    detector = RecurringTopicsDetector()

    messages = [
        "¿Cómo puedo cambiar mi contraseña?",
        "¿Cómo actualizo mi perfil?",
    ]

    results = detector.detect(messages)

    assert results == []


def test_includes_message_examples():
    detector = RecurringTopicsDetector()

    messages = [
        "¿Cómo puedo cambiar mi contraseña?",
        "¿Dónde puedo cambiar la contraseña?",
    ]

    results = detector.detect(messages)

    assert len(results) == 1
    assert len(results[0].examples) == 2
    assert messages[0] in results[0].examples
    assert messages[1] in results[0].examples


def test_suggests_faq_title():
    detector = RecurringTopicsDetector()

    messages = [
        "¿Cómo puedo cambiar mi contraseña?",
        "¿Dónde puedo cambiar la contraseña?",
    ]

    results = detector.detect(messages)

    assert results[0].faq_title == "Preguntas frecuentes sobre contraseña"

def test_topics_are_sorted_by_frequency():
    detector = RecurringTopicsDetector()

    messages = [
        "¿Cómo cambio mi contraseña?",
        "¿Dónde cambio mi contraseña?",
        "¿Cómo actualizo mi perfil?",
        "¿Cómo cambio mi perfil?",
        "¿Dónde cambio mi perfil?",
    ]

    results = detector.detect(messages)

    assert len(results) == 2
    assert results[0].count >= results[1].count


def test_minimum_occurrences_can_be_configured():
    detector = RecurringTopicsDetector(min_occurrences=3)

    messages = [
        "¿Cómo puedo cambiar mi contraseña?",
        "¿Dónde puedo cambiar la contraseña?",
    ]

    results = detector.detect(messages)

    assert results == []

def test_groups_singular_and_plural_topics():
    detector = RecurringTopicsDetector()
    messages = [
        "¿Cómo cambio mi contraseña?",
        "¿Cómo cambio mis contraseñas?",
    ]

    results = detector.detect(messages)

    assert len(results) == 1
    assert results[0].topic == "contraseña"
    assert results[0].count == 2

def test_rejects_min_occurrences_below_two():
    with pytest.raises(ValueError):
        RecurringTopicsDetector(min_occurrences=1)


def test_returns_empty_for_stopwords_only_message():
    detector = RecurringTopicsDetector()
    assert detector.detect(["¿Qué puedo hacer?"]) == []


def test_returns_empty_for_empty_message_list():
    detector = RecurringTopicsDetector()
    assert detector.detect([]) == []


@pytest.mark.parametrize("a,b", [
    ("mensaje", "mensajes"),
    ("clave", "claves"),
    ("notificación", "notificaciones"),
])
def test_groups_plural_variants(a, b):
    detector = RecurringTopicsDetector()
    results = detector.detect([a, b])

    assert len(results) == 1
    assert results[0].count == 2