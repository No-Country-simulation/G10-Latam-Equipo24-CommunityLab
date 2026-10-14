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


def test_format_relevancia_renders_whole_percentage():
    texto = telegram_publish.format_candidate_message(
        {"copy": "Copy", "relevancia": 0.75}
    )

    assert "Relevancia: 75%" in texto


def test_format_footer_fields_only_when_present():
    texto = telegram_publish.format_candidate_message(
        {
            "titulo": "T",
            "copy": "C",
            "canal_recomendado": "LinkedIn Oficial",
            "autor": "Mariana",
            "relevancia": 0.5,
        }
    )

    assert "Canal sugerido: LinkedIn Oficial" in texto
    assert "Autor: Mariana" in texto
    assert "Relevancia: 50%" in texto


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
