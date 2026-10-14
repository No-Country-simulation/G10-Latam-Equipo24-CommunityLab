"""Unit tests for src.interface.telegram_publish (no network, no real token).

The transport (`src.ingest.bot.send_message`) is always replaced by a fake
sender or by injectable ``env`` so these tests never read the developer
environment and never touch the Telegram API.
"""

import pytest

from src.interface import telegram_publish


# ---------------------------------------------------------------------------
# format_candidate_message
# ---------------------------------------------------------------------------


def test_format_includes_titulo_and_copy_in_order():
    texto = telegram_publish.format_candidate_message(
        {"titulo": "Titulo de prueba", "copy": "Copy de prueba"}
    )

    assert "Titulo de prueba" in texto
    assert "Copy de prueba" in texto
    assert texto.index("Titulo de prueba") < texto.index("Copy de prueba")


def test_format_with_only_copy_does_not_start_with_blank_line():
    texto = telegram_publish.format_candidate_message({"copy": "Solo copy"})

    assert texto == "Solo copy"
    assert not texto.startswith("\n")


def test_format_empty_fields_do_not_emit_labels():
    texto = telegram_publish.format_candidate_message(
        {
            "titulo": "Titulo",
            "copy": "Copy",
            "canal_recomendado": "",
            "autor": "",
            "relevancia": None,
        }
    )

    assert "Canal sugerido:" not in texto
    assert "Autor:" not in texto
    assert "Relevancia:" not in texto


def test_format_missing_keys_are_treated_as_empty():
    texto = telegram_publish.format_candidate_message({})

    assert texto == ""


def test_format_joins_titulo_blank_line_and_copy():
    texto = telegram_publish.format_candidate_message(
        {"titulo": "Titulo", "copy": "Copy"}
    )

    assert texto == "Titulo\n\nCopy"


def test_format_relevancia_is_never_part_of_the_message():
    texto = telegram_publish.format_candidate_message(
        {"copy": "Copy", "relevancia": 0.75}
    )

    assert "Relevancia" not in texto
    assert "75%" not in texto


def test_format_footer_fields_are_never_emitted():
    texto = telegram_publish.format_candidate_message(
        {
            "titulo": "T",
            "copy": "C",
            "canal_recomendado": "LinkedIn Oficial",
            "autor": "Mariana",
            "relevancia": 0.5,
        }
    )

    assert "Canal sugerido: LinkedIn Oficial" not in texto
    assert "Autor: Mariana" not in texto
    assert "Relevancia: 50%" not in texto


def test_format_full_candidate_publishes_post_body_only():
    """A candidate WITH canal/autor/relevancia publishes only titulo + copy."""
    texto = telegram_publish.format_candidate_message(
        {
            "titulo": "Titulo de Mariana",
            "copy": "Copy de Mariana",
            "canal_recomendado": "LinkedIn de Mariana",
            "autor": "Mariana Souza",
            "relevancia": 0.95,
            "potencial_engagement": "Alto",
        }
    )

    assert texto == "Titulo de Mariana\n\nCopy de Mariana"
    assert "Canal sugerido" not in texto
    assert "Autor:" not in texto
    assert "Relevancia" not in texto


# ---------------------------------------------------------------------------
# publish_candidate — configuration
# ---------------------------------------------------------------------------


def test_publish_candidate_missing_token_names_env_var():
    with pytest.raises(telegram_publish.TelegramConfigError) as excinfo:
        telegram_publish.publish_candidate({"copy": "x"}, env={})

    assert "TELEGRAM_BOT_TOKEN" in str(excinfo.value)


def test_publish_candidate_missing_chat_id_names_env_var():
    with pytest.raises(telegram_publish.TelegramConfigError) as excinfo:
        telegram_publish.publish_candidate(
            {"copy": "x"}, env={"TELEGRAM_BOT_TOKEN": "token-de-prueba"}
        )

    assert "TELEGRAM_CHAT_ID" in str(excinfo.value)


def test_publish_candidate_missing_config_does_not_send():
    llamadas = []

    def fake_sender(token, chat_id, text):
        llamadas.append((token, chat_id, text))

    with pytest.raises(telegram_publish.TelegramConfigError):
        telegram_publish.publish_candidate(
            {"copy": "x"}, sender=fake_sender, env={}
        )

    assert llamadas == []


def test_telegram_config_error_is_a_value_error():
    assert issubclass(telegram_publish.TelegramConfigError, ValueError)


# ---------------------------------------------------------------------------
# describe_destination — destino sin lanzar excepciones
# ---------------------------------------------------------------------------


def test_describe_destination_returns_chat_when_configured():
    destino = telegram_publish.describe_destination(
        env={"TELEGRAM_BOT_TOKEN": "tok-que-no-debe-aparecer", "TELEGRAM_CHAT_ID": "7191785744"}
    )

    assert destino == "Se va a publicar en el chat 7191785744"
    assert "tok-que-no-debe-aparecer" not in destino


def test_describe_destination_returns_none_when_token_missing():
    destino = telegram_publish.describe_destination(env={"TELEGRAM_CHAT_ID": "12345"})

    assert destino is None


def test_describe_destination_returns_none_when_chat_id_missing():
    destino = telegram_publish.describe_destination(env={"TELEGRAM_BOT_TOKEN": "tok"})

    assert destino is None


def test_describe_destination_returns_none_without_any_config():
    assert telegram_publish.describe_destination(env={}) is None


# ---------------------------------------------------------------------------
# publish_signature — identidad del candidato + copy editado
# ---------------------------------------------------------------------------


def test_publish_signature_changes_when_copy_is_edited():
    base = {"titulo": "T", "autor": "A", "copy": "original"}
    editado = dict(base, copy="editado")

    assert telegram_publish.publish_signature(base) != telegram_publish.publish_signature(editado)


def test_publish_signature_changes_for_a_different_candidate():
    uno = {"titulo": "T uno", "autor": "A", "copy": "mismo copy"}
    otro = {"titulo": "T otro", "autor": "B", "copy": "mismo copy"}

    assert telegram_publish.publish_signature(uno) != telegram_publish.publish_signature(otro)


def test_publish_signature_is_stable_for_same_candidate_and_copy():
    a = {"titulo": "T", "autor": "A", "copy": "C"}
    b = {"titulo": "  T  ", "autor": "A", "copy": "C\n"}

    assert telegram_publish.publish_signature(a) == telegram_publish.publish_signature(b)


# ---------------------------------------------------------------------------
# publish_candidate — success and error paths
# ---------------------------------------------------------------------------


def test_publish_candidate_success_records_and_returns_sent_text():
    registros = []

    def fake_sender(token, chat_id, text):
        registros.append((token, chat_id, text))

    candidato = {"titulo": "T", "copy": "C", "relevancia": 0.75}
    esperado = telegram_publish.format_candidate_message(candidato)

    devuelto = telegram_publish.publish_candidate(
        candidato,
        sender=fake_sender,
        env={"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "12345"},
    )

    assert registros == [("tok", "12345", esperado)]
    assert devuelto == esperado


def test_publish_candidate_transport_error_does_not_leak_token():
    token_secreto = "123456:SECRETO-QUE-NO-DEBE-SALIR"

    def sender_fallido(token, chat_id, text):
        raise RuntimeError(
            "Telegram respondió HTTP 401 al enviar sendMessage. "
            "Revisá el token (401 = inválido)."
        )

    with pytest.raises(RuntimeError) as excinfo:
        telegram_publish.publish_candidate(
            {"copy": "x"},
            sender=sender_fallido,
            env={"TELEGRAM_BOT_TOKEN": token_secreto, "TELEGRAM_CHAT_ID": "1"},
        )

    assert token_secreto not in str(excinfo.value)
