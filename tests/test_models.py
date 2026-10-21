"""Tests for domain models (contract)."""
from src.domain.models import (
    CommunitySummary,
    DerivedMessage,
    DistributionAssets,
    FAQCandidate,
    FAQSuggestion,
    InputMessage,
    InputBatch,
    SentimentResult,
    SentimentType,
    OutputBatch,
    TopicFrequency,
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


def test_community_summary_feedback_negativo_defaults_to_zero():
    """`feedback_negativo` is additive: existing summaries keep working."""
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Neutro",
    )
    assert summary.feedback_negativo == 0


def test_community_summary_feedback_negativo_accepts_value():
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Negativo",
        feedback_negativo=2,
    )
    assert summary.feedback_negativo == 2


def test_community_summary_dudas_frecuentes_defaults_to_zero():
    """`dudas_frecuentes` is additive: existing summaries keep working."""
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Neutro",
    )
    assert summary.dudas_frecuentes == 0


def test_community_summary_dudas_frecuentes_accepts_value():
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Neutro",
        dudas_frecuentes=4,
    )
    assert summary.dudas_frecuentes == 4


# ---------------------------------------------------------------------------
# Option A additive fields (HU-S4-003): sentiment distribution + counted topics
# ---------------------------------------------------------------------------


def test_community_summary_option_a_fields_default_empty():
    """The Option A fields are additive: both default to empty."""
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Neutro",
    )
    assert summary.distribucion_sentimiento == {}
    assert summary.temas_principales_conteo == []


def test_community_summary_option_a_fields_accept_values():
    summary = CommunitySummary(
        total_interacciones_procesadas=3,
        sentimiento_predominante="Positivo",
        distribucion_sentimiento={"positivo": 2, "neutral": 1},
        temas_principales_conteo=[
            TopicFrequency(tema="python", conteo=2),
            TopicFrequency(tema="ia", conteo=1),
        ],
    )
    assert summary.distribucion_sentimiento == {"positivo": 2, "neutral": 1}
    assert [tf.tema for tf in summary.temas_principales_conteo] == ["python", "ia"]
    assert summary.temas_principales_conteo[0].conteo == 2


def test_community_summary_option_a_fields_serialize_roundtrip():
    summary = CommunitySummary(
        total_interacciones_procesadas=2,
        sentimiento_predominante="Positivo",
        distribucion_sentimiento={"positivo": 2},
        temas_principales_conteo=[TopicFrequency(tema="logro", conteo=2)],
    )
    payload = summary.model_dump()
    assert payload["distribucion_sentimiento"] == {"positivo": 2}
    assert payload["temas_principales_conteo"] == [{"tema": "logro", "conteo": 2}]

    restored = CommunitySummary.model_validate_json(summary.model_dump_json())
    assert restored.distribucion_sentimiento == {"positivo": 2}
    assert restored.temas_principales_conteo[0].tema == "logro"
    assert restored.temas_principales_conteo[0].conteo == 2


def test_community_summary_without_option_a_keys_still_deserializes():
    """Additive guarantee: a summary serialized before Option A (no new keys)
    still deserializes and exposes the empty defaults."""
    legacy = {
        "total_interacciones_procesadas": 3,
        "sentimiento_predominante": "Neutro",
        "temas_principales": ["python"],
        "analisis_degradados": 1,
        "feedback_negativo": 0,
    }
    summary = CommunitySummary.model_validate(legacy)

    assert summary.distribucion_sentimiento == {}
    assert summary.temas_principales_conteo == []


# ---------------------------------------------------------------------------
# Derivación a humano (B): DerivedMessage + DistributionAssets.mensajes_derivados
# ---------------------------------------------------------------------------


def test_derived_message_carries_author_channel_text_reason_confidence():
    """DerivedMessage exposes the fields the operator inbox needs."""
    dm = DerivedMessage(
        message_id="m-1",
        autor="Nora",
        canal="#general",
        texto_original="No me gustó el taller.",
        razon="Feedback negativo: requiere atención personalizada",
        confianza=0.85,
    )
    assert dm.autor == "Nora"
    assert dm.canal == "#general"
    assert dm.texto_original == "No me gustó el taller."
    assert dm.razon == "Feedback negativo: requiere atención personalizada"
    assert dm.confianza == 0.85


def test_distribution_assets_mensajes_derivados_defaults_empty():
    """mensajes_derivados is additive: old outputs deserialize as empty."""
    assets = DistributionAssets()
    assert assets.mensajes_derivados == []


def test_distribution_assets_mensajes_derivados_accepts_list():
    dm = DerivedMessage(
        message_id="m-1",
        autor="Nora",
        canal="#general",
        texto_original="No me gustó el taller.",
        razon="Feedback negativo",
        confianza=0.85,
    )
    assets = DistributionAssets(mensajes_derivados=[dm])
    assert len(assets.mensajes_derivados) == 1
    assert assets.mensajes_derivados[0].autor == "Nora"


def test_distribution_assets_legacy_payload_without_derivados_deserializes():
    """A DistributionAssets payload without mensajes_derivados still loads."""
    legacy = {
        "post_linkedin": None,
        "destaque_newsletter_semanal": None,
        "sugerencia_contenido_faq": None,
        "candidatos_post_linkedin": [],
        "candidatos_faq": [],
    }
    assets = DistributionAssets.model_validate(legacy)
    assert assets.mensajes_derivados == []


# ---------------------------------------------------------------------------
# FAQ semantic consolidation (C): FAQSuggestion extension + DistributionAssets.temas_faq
# ---------------------------------------------------------------------------


def test_faq_suggestion_carries_respuesta_and_preguntas_relacionadas():
    """Extended FAQSuggestion exposes a generated answer and related questions."""
    suggestion = FAQSuggestion(
        tema="Configurar retry en Mastodon",
        origen="#dudas",
        status="generado",
        respuesta="Se configura desde el panel de administración.",
        preguntas_relacionadas=["¿Cómo configuro el retry?"],
    )
    assert suggestion.tema == "Configurar retry en Mastodon"
    assert suggestion.respuesta == "Se configura desde el panel de administración."
    assert suggestion.preguntas_relacionadas == ["¿Cómo configuro el retry?"]
    assert suggestion.status == "generado"


def test_faq_suggestion_respuesta_and_preguntas_default_empty():
    """Additive extension: old suggestions without the new fields still validate."""
    legacy = {"tema": "Tema viejo", "origen": "#general", "status": "derivado_a_mentoria"}
    suggestion = FAQSuggestion.model_validate(legacy)
    assert suggestion.respuesta == ""
    assert suggestion.preguntas_relacionadas == []


def test_distribution_assets_temas_faq_defaults_empty():
    """temas_faq is additive: old outputs deserialize as empty."""
    assets = DistributionAssets()
    assert assets.temas_faq == []


def test_distribution_assets_temas_faq_accepts_list():
    theme = FAQSuggestion(
        tema="Retry en Mastodon",
        respuesta="Desde el panel.",
        preguntas_relacionadas=["¿Cómo?"],
    )
    assets = DistributionAssets(temas_faq=[theme])
    assert len(assets.temas_faq) == 1
    assert assets.temas_faq[0].respuesta == "Desde el panel."


def test_distribution_assets_legacy_payload_without_temas_faq_deserializes():
    """A DistributionAssets payload without temas_faq still loads."""
    legacy = {
        "post_linkedin": None,
        "destaque_newsletter_semanal": None,
        "sugerencia_contenido_faq": None,
        "candidatos_post_linkedin": [],
        "candidatos_faq": [],
        "mensajes_derivados": [],
    }
    assets = DistributionAssets.model_validate(legacy)
    assert assets.temas_faq == []


def test_faq_candidate_carries_topics_for_clustering():
    """FAQCandidate now carries topics so clustering can group by theme."""
    candidate = FAQCandidate(
        autor="Ana",
        canal="#dudas",
        texto_original="¿Cómo configuro el retry?",
        relevancia=0.9,
        topics=["configuración", "mastodon"],
    )
    assert candidate.topics == ["configuración", "mastodon"]
