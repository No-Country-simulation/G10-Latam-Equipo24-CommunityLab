from src.ingest.bot import run_bot


def _update(update_id, chat_id, chat_type="private", text="Mensaje de prueba"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
        },
    }


def test_no_reenvia_las_respuestas_exitosas_si_falla_la_tercera(monkeypatch):
    updates = [
        _update(1, 101),
        _update(2, 102),
        _update(3, 103),
    ]
    offsets = []
    enviados = []
    fallo_tercero = {"pendiente": True}

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        return [
            update
            for update in updates
            if offset is None or update["update_id"] >= offset
        ]

    def fake_send(token, chat_id, text):
        enviados.append(chat_id)
        if chat_id == 103 and fallo_tercero["pendiente"]:
            fallo_tercero["pendiente"] = False
            raise RuntimeError("Error de red simulado")

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr("src.ingest.bot.build_reply", lambda text: "Respuesta de prueba")
    monkeypatch.setattr("src.ingest.bot.apply_backend", lambda backend: None)
    monkeypatch.setattr("src.ingest.bot._sleep", lambda segundos: None)

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    assert offsets == [None, 3]
    assert enviados == [101, 102, 103, 103]


def test_ignora_grupos_y_confirma_sus_actualizaciones(monkeypatch):
    updates = [
        _update(1, 101, "private"),
        _update(2, -100123, "supergroup"),
        _update(3, 103, "private"),
    ]
    offsets = []
    enviados = []

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        return [
            update
            for update in updates
            if offset is None or update["update_id"] >= offset
        ]

    def fake_send(token, chat_id, text):
        enviados.append(chat_id)

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr("src.ingest.bot.build_reply", lambda text: "Respuesta de prueba")
    monkeypatch.setattr("src.ingest.bot.apply_backend", lambda backend: None)

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    assert enviados == [101, 103]
    assert offsets == [None, 4]

    
def test_error_401_detiene_el_bot_sin_reintentos(monkeypatch):
    import pytest
    from src.ingest.telegram import TelegramAuthError

    llamadas = []
    pausas = []

    def fake_fetch(token, offset=None, poll_timeout=None):
        llamadas.append(offset)
        raise TelegramAuthError("Credenciales inválidas (HTTP 401).")

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.apply_backend", lambda backend: None)
    monkeypatch.setattr("src.ingest.bot._sleep", lambda segundos: pausas.append(segundos))

    with pytest.raises(TelegramAuthError):
        run_bot("token-de-prueba", backend="rule_based", max_cycles=3)

    assert len(llamadas) == 1
    assert pausas == []


def test_error_permanente_no_bloquea_los_siguientes_mensajes(monkeypatch):
    from src.ingest.telegram import TelegramPermanentError

    updates = [
        _update(1, 101),
        _update(2, 102),
        _update(3, 103),
        _update(4, 104),
    ]
    offsets = []
    enviados = []
    intentos_fallidos = {"cantidad": 0}

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        return [
            update
            for update in updates
            if offset is None or update["update_id"] >= offset
        ]

    def fake_send(token, chat_id, text):
        enviados.append(chat_id)
        if chat_id == 103:
            intentos_fallidos["cantidad"] += 1
            raise TelegramPermanentError("Error permanente simulado.")

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr("src.ingest.bot.build_reply", lambda text: "Respuesta de prueba")
    monkeypatch.setattr("src.ingest.bot.apply_backend", lambda backend: None)
    monkeypatch.setattr("src.ingest.bot._sleep", lambda segundos: None)

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    assert intentos_fallidos["cantidad"] == 3
    assert enviados == [101, 102, 103, 103, 103, 104]
    assert offsets == [None, 5]


def test_error_permanente_al_consultar_detiene_el_bot(monkeypatch):
    import pytest
    from src.ingest.telegram import TelegramPermanentError

    llamadas = []
    pausas = []

    def fake_fetch(token, offset=None, poll_timeout=None):
        llamadas.append(offset)
        raise TelegramPermanentError("Error permanente simulado.")

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.apply_backend", lambda backend: None)
    monkeypatch.setattr(
        "src.ingest.bot._sleep",
        lambda segundos: pausas.append(segundos),
    )

    with pytest.raises(TelegramPermanentError):
        run_bot("token-de-prueba", backend="rule_based", max_cycles=3)

    assert len(llamadas) == 1
    assert pausas == []


def test_error_permanente_seguido_de_temporal_conserva_offset_y_reintenta(
    monkeypatch,
):
    from src.ingest.telegram import (
        TelegramPermanentError,
        TelegramTransientError,
    )

    updates = [
        _update(1, 101),
        _update(2, 102),
        _update(3, 103),
    ]
    offsets = []
    enviados = []
    intentos_tercero = {"cantidad": 0}

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        return [
            update
            for update in updates
            if offset is None or update["update_id"] >= offset
        ]


    def fake_send(token, chat_id, text):
        enviados.append(chat_id)

        if chat_id == 103:
            intentos_tercero["cantidad"] += 1
            intento = intentos_tercero["cantidad"]

            if intento <= 2:
                raise TelegramPermanentError(
                    "Error permanente simulado."
                )

            if intento == 3:
                raise TelegramTransientError(
                    "Error temporal simulado."
                )

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr(
        "src.ingest.bot.build_reply",
        lambda text: "Respuesta de prueba",
    )
    monkeypatch.setattr(
        "src.ingest.bot.apply_backend",
        lambda backend: None,
    )
    monkeypatch.setattr("src.ingest.bot._sleep", lambda segundos: None)

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    # Las dos primeras actualizaciones no deben reprocesarse.
    assert enviados == [101, 102, 103, 103, 103, 103]

    # Tras el fallo temporal, se conserva el offset de la tercera.
    assert offsets == [None, 3]

    # La tercera actualización termina procesándose en el segundo ciclo.
    assert intentos_tercero["cantidad"] == 4


def test_elemento_invalido_interrumpe_lote_y_aplica_espera(monkeypatch):
    offsets = []
    pausas = []
    enviados = []
    ciclos = {"cantidad": 0}

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        ciclos["cantidad"] += 1

        if ciclos["cantidad"] == 1:
            return [
                _update(1, 101),
                None,
                _update(3, 103),
            ]

        return []

    def fake_send(token, chat_id, text):
        enviados.append(chat_id)

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr(
        "src.ingest.bot.build_reply",
        lambda text: "Respuesta de prueba",
    )
    monkeypatch.setattr(
        "src.ingest.bot.apply_backend",
        lambda backend: None,
    )
    monkeypatch.setattr(
        "src.ingest.bot._sleep",
        lambda segundos: pausas.append(segundos),
    )

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    assert enviados == [101]
    assert offsets == [None, 2]
    assert pausas == [1]

def test_update_sin_id_conserva_offset_y_aplica_espera(monkeypatch):
    offsets = []
    pausas = []
    enviados = []
    ciclos = {"cantidad": 0}

    actualizacion_invalida = {
        "message": {
            "message_id": 2,
            "chat": {"id": 102, "type": "private"},
            "text": "Mensaje sin identificador de actualización",
        }
    }

    def fake_fetch(token, offset=None, poll_timeout=None):
        offsets.append(offset)
        ciclos["cantidad"] += 1

        if ciclos["cantidad"] == 1:
            return [
                _update(1, 101),
                actualizacion_invalida,
                _update(3, 103),
            ]

        return []

    def fake_send(token, chat_id, text):
        enviados.append(chat_id)

    monkeypatch.setattr("src.ingest.bot.fetch_updates", fake_fetch)
    monkeypatch.setattr("src.ingest.bot.send_message", fake_send)
    monkeypatch.setattr(
        "src.ingest.bot.build_reply",
        lambda text: "Respuesta de prueba",
    )
    monkeypatch.setattr(
        "src.ingest.bot.apply_backend",
        lambda backend: None,
    )
    monkeypatch.setattr(
        "src.ingest.bot._sleep",
        lambda segundos: pausas.append(segundos),
    )

    run_bot("token-de-prueba", backend="rule_based", max_cycles=2)

    assert enviados == [101]
    assert offsets == [None, 2]
    assert pausas == [1]
