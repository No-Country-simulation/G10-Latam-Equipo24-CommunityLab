"""Tests for domain models (contract)."""
from src.domain.models import (
    InputMessage,
    InputBatch,
    SentimentResult,
    SentimentType,
    OutputBatch,
)


def test_input_message_accepts_contract_fields():
    """InputMessage uses the contract fields: autor/canal/tipo/texto."""
    data = {
        "autor": "Mariana Souza",
        "canal": "#logros-y-empleos",
        "tipo": "testimonio",
        "texto": "Consegui mi primer trabajo como dev.",
    }
    msg = InputMessage(**data)
    assert msg.autor == "Mariana Souza"
    assert msg.canal == "#logros-y-empleos"
    assert msg.tipo == "testimonio"
    assert msg.texto.startswith("Consegui")


def test_input_message_optional_fields():
    """`id` and `timestamp` are NOT required (the PDF example lacks them)."""
    msg = InputMessage(
        autor="a",
        canal="#c",
        tipo="testimonio",
        texto="t",
        id="msg-1",
        timestamp="2026-09-15T14:30:00Z",
    )
    assert msg.id == "msg-1"
    assert msg.timestamp == "2026-09-15T14:30:00Z"

    # without id/timestamp is also valid
    msg2 = InputMessage(autor="a", canal="#c", tipo="t", texto="t")
    assert msg2.id is None
    assert msg2.timestamp is None


def test_input_batch_parses_envelope():
    batch = InputBatch(
        origen_comunidad="Discord_Grupo_ONE_G10",
        periodo_referencia="Semana_04",
        interacciones=[
            InputMessage(
                autor="Mariana", canal="#logros", tipo="testimonio", texto="..."
            )
        ],
    )
    assert batch.origen_comunidad == "Discord_Grupo_ONE_G10"
    assert batch.periodo_referencia == "Semana_04"
    assert len(batch.interacciones) == 1


def test_sentiment_result():
    result = SentimentResult(
        message_id="msg-003",
        sentiment=SentimentType.POSITIVO,
        score=0.95,
        reasoning="Test",
    )
    assert result.message_id == "msg-003"
    assert result.sentiment == SentimentType.POSITIVO


def test_output_batch_uses_contract_keys():
    """OutputBatch uses the exact contract keys."""
    batch = OutputBatch(
        status="exito",
        resumen_comunidad={
            "total_interacciones_procesadas": 2,
            "sentimiento_predominante": "Altamente Positivo",
            "temas_principales": ["Contratacion / Logros"],
        },
        activos_distribucion_generados={},
        almacenamiento_oci={
            "bucket": "communitylab-activos-marketing",
            "ruta_objeto": "activos/2026-semana-04/paquete-distribucion.json",
            "status": "guardado_con_exito",
        },
    )
    assert batch.status == "exito"
    assert batch.resumen_comunidad.total_interacciones_procesadas == 2
    assert set(batch.model_dump().keys()) == {
        "status",
        "resumen_comunidad",
        "activos_distribucion_generados",
        "almacenamiento_oci",
    }
