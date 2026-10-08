import pytest

from src.decisions.recurring_topics import RecurringTopicsDetector
from src.domain.models import (
    AnalysisComplete,
    CategorizationResult,
    InputMessage,
)


def make_analysis(
    message_id: str,
    topics: list[str],
) -> AnalysisComplete:
    return AnalysisComplete(
        message_id=message_id,
        categorization=CategorizationResult(
            message_id=message_id,
            category="pregunta_tecnica",
            topics=topics,
        ),
    )


def make_message(
    message_id: str,
    text: str,
) -> InputMessage:
    return InputMessage(
        id=message_id,
        autor="test",
        canal="discord",
        tipo="pregunta",
        texto=text,
    )


def test_detects_recurring_topic_from_analysis_topics():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "¿Cómo puedo cambiar mi contraseña?"),
            make_analysis("1", ["contraseña"]),
        ),
        (
            make_message("2", "¿Dónde puedo cambiar la contraseña?"),
            make_analysis("2", ["contraseña"]),
        ),
        (
            make_message("3", "¿Cómo actualizo mi perfil?"),
            make_analysis("3", ["perfil"]),
        ),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert results[0].topic == "contraseña"
    assert results[0].count == 2


def test_ignores_topics_with_one_occurrence():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "¿Cómo puedo cambiar mi contraseña?"),
            make_analysis("1", ["contraseña"]),
        ),
        (
            make_message("2", "¿Cómo actualizo mi perfil?"),
            make_analysis("2", ["perfil"]),
        ),
    ]

    results = detector.detect(inputs)

    assert results == []


def test_includes_message_examples():
    detector = RecurringTopicsDetector()

    message_1 = make_message("1", "¿Cómo puedo cambiar mi contraseña?")
    message_2 = make_message("2", "¿Dónde puedo cambiar la contraseña?")

    inputs = [
        (message_1, make_analysis("1", ["contraseña"])),
        (message_2, make_analysis("2", ["contraseña"])),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert len(results[0].examples) == 2
    assert message_1.texto in results[0].examples
    assert message_2.texto in results[0].examples


def test_suggests_faq_title():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "¿Cómo puedo cambiar mi contraseña?"),
            make_analysis("1", ["contraseña"]),
        ),
        (
            make_message("2", "¿Dónde puedo cambiar la contraseña?"),
            make_analysis("2", ["contraseña"]),
        ),
    ]

    results = detector.detect(inputs)

    assert results[0].faq_title == "Preguntas frecuentes sobre contraseña"


def test_topics_are_sorted_by_frequency():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "¿Cómo cambio mi contraseña?"),
            make_analysis("1", ["contraseña"]),
        ),
        (
            make_message("2", "¿Dónde cambio mi contraseña?"),
            make_analysis("2", ["contraseña"]),
        ),
        (
            make_message("3", "¿Cómo actualizo mi perfil?"),
            make_analysis("3", ["perfil"]),
        ),
        (
            make_message("4", "¿Cómo cambio mi perfil?"),
            make_analysis("4", ["perfil"]),
        ),
        (
            make_message("5", "¿Dónde cambio mi perfil?"),
            make_analysis("5", ["perfil"]),
        ),
    ]

    results = detector.detect(inputs)

    assert len(results) == 2
    assert results[0].count >= results[1].count


def test_minimum_occurrences_can_be_configured():
    detector = RecurringTopicsDetector(min_occurrences=3)

    inputs = [
        (
            make_message("1", "¿Cómo puedo cambiar mi contraseña?"),
            make_analysis("1", ["contraseña"]),
        ),
        (
            make_message("2", "¿Dónde puedo cambiar la contraseña?"),
            make_analysis("2", ["contraseña"]),
        ),
    ]

    results = detector.detect(inputs)

    assert results == []


def test_rejects_min_occurrences_below_two():
    with pytest.raises(ValueError):
        RecurringTopicsDetector(min_occurrences=1)


def test_returns_empty_for_empty_input():
    detector = RecurringTopicsDetector()

    assert detector.detect([]) == []


def test_uses_all_topics_from_analysis():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Tengo problemas con Docker y Git"),
            make_analysis("1", ["docker", "git"]),
        ),
        (
            make_message("2", "No entiendo Docker"),
            make_analysis("2", ["docker"]),
        ),
        (
            make_message("3", "No entiendo Git"),
            make_analysis("3", ["git"]),
        ),
    ]

    results = detector.detect(inputs)

    topics = {result.topic: result.count for result in results}

    assert topics == {
        "docker": 2,
        "git": 2,
    }


def test_ignores_analysis_without_categorization():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Mensaje sin categorización"),
            AnalysisComplete(message_id="1"),
        ),
        (
            make_message("2", "Otro mensaje sin categorización"),
            AnalysisComplete(message_id="2"),
        ),
    ]

    results = detector.detect(inputs)

    assert results == []


def test_ignores_empty_topics():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Mensaje sin topics"),
            make_analysis("1", []),
        ),
        (
            make_message("2", "Otro mensaje sin topics"),
            make_analysis("2", []),
        ),
    ]

    results = detector.detect(inputs)

    assert results == []


def test_returns_empty_for_none_input():
    detector = RecurringTopicsDetector()

    assert detector.detect(None) == []


def test_returns_empty_for_invalid_input_type():
    detector = RecurringTopicsDetector()

    assert detector.detect({"message": "esto no es válido"}) == []


def test_keeps_message_analysis_pair_associated():
    detector = RecurringTopicsDetector()

    message_1 = make_message("1", "No puedo usar Docker")
    message_2 = make_message("2", "Tengo problemas con Docker")

    inputs = [
        (message_1, make_analysis("1", ["docker"])),
        (message_2, make_analysis("2", ["docker"])),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert results[0].count == 2
    assert message_1.texto in results[0].examples
    assert message_2.texto in results[0].examples


def test_deduplicates_topics_within_same_message():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Tengo problemas con Docker"),
            make_analysis("1", ["docker", "docker"]),
        ),
        (
            make_message("2", "No puedo usar Docker"),
            make_analysis("2", ["docker"]),
        ),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert results[0].topic == "docker"
    assert results[0].count == 2


def test_normalizes_topic_case_across_messages():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Tengo problemas con Docker"),
            make_analysis("1", ["Docker"]),
        ),
        (
            make_message("2", "No puedo usar docker"),
            make_analysis("2", ["docker"]),
        ),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert results[0].topic == "docker"
    assert results[0].count == 2


def test_normalizes_topic_accents_across_messages():
    detector = RecurringTopicsDetector()

    inputs = [
        (
            make_message("1", "Olvidé mi CONTRASEÑA"),
            make_analysis("1", ["CONTRASEÑA"]),
        ),
        (
            make_message("2", "No recuerdo mi contraseña"),
            make_analysis("2", ["contraseña"]),
        ),
    ]

    results = detector.detect(inputs)

    assert len(results) == 1
    assert results[0].topic == "contraseña"
    assert results[0].count == 2
