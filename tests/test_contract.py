"""Data contract tests — CommunityLab.

This file is THE safety net of the project: it verifies that the models accept
EXACTLY the input/output example of the challenge (PDF).

If this test fails, something broke the contract and it must NOT be merged.

Run from the repo root:
    python3 -m pytest tests/test_contract.py -q
"""
from src.domain.models import (
    CommunitySummary,
    InputBatch,
    OutputBatch,
)

# ---------------------------------------------------------------------------
# The LITERAL example from the PDF (Desafio 3 - CommunityLab).
# NOTE: this is test DATA (the contract example), so it stays in Spanish.
# ---------------------------------------------------------------------------

ENTRADA_EJEMPLO = {
    "origen_comunidad": "Discord_Grupo_ONE_G10",
    "periodo_referencia": "Semana_04",
    "interacciones": [
        {
            "autor": "Mariana Souza",
            "canal": "#logros-y-empleos",
            "tipo": "testimonio",
            "texto": (
                "Comunidad, quede seleccionada para el puesto de Desarrolladora "
                "Junior de IA! El proyecto del curso de LangChain y OCI que "
                "construi en mi portfolio marco toda la diferencia en la "
                "entrevista tecnica."
            ),
        },
        {
            "autor": "Lucas Albuquerque",
            "canal": "#dudas-langgraph",
            "tipo": "pregunta_tecnica",
            "texto": (
                "Tengo dudas sobre como estructurar los nodos condicionales en "
                "LangGraph cuando la respuesta del LLM necesita reintento."
            ),
        },
    ],
}

SALIDA_EJEMPLO = {
    "status": "exito",
    "resumen_comunidad": {
        "total_interacciones_procesadas": 2,
        "sentimiento_predominante": "Altamente Positivo",
        "temas_principales": [
            "Contratacion / Logros",
            "LangGraph / Nodos Condicionales",
        ],
    },
    "activos_distribucion_generados": {
        "post_linkedin": {
            "titulo": "De la Comunidad al Mercado: El impacto de los proyectos practicos de IA",
            "copy": "Nada nos da mas orgullo que ver a nuestros talentos conquistando el mercado!",
            "canal_recomendado": "LinkedIn Oficial",
            "potencial_engagement": "Alto",
        },
        "destaque_newsletter_semanal": {
            "seccion": "Logro de la Semana",
            "titular": "Estudiante consigue empleo dev con portfolio de IA en Oracle Cloud",
            "resumen": "Mariana Souza obtuvo su primera oportunidad como Dev Jr de IA.",
        },
        "sugerencia_contenido_faq": {
            "tema": "Tip Rapido: Como crear nodos de reintento en LangGraph",
            "origen": "Duda frecuente planteada por Lucas Albuquerque en el canal de soporte",
            "status": "derivado_a_mentoria",
        },
    },
    "almacenamiento_oci": {
        "bucket": "communitylab-activos-marketing",
        "ruta_objeto": "activos/2026-semana-04/paquete-distribucion.json",
        "status": "guardado_con_exito",
    },
}


# ---------------------------------------------------------------------------
# INPUT tests
# ---------------------------------------------------------------------------

def test_input_accepts_literal_example():
    """The PDF input example must parse without validation errors."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    assert batch.origen_comunidad == "Discord_Grupo_ONE_G10"
    assert batch.periodo_referencia == "Semana_04"
    assert len(batch.interacciones) == 2


def test_tipo_is_preserved():
    """`tipo` must not be lost: it is the decision engine's routing signal."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    tipos = [i.tipo for i in batch.interacciones]
    assert tipos == ["testimonio", "pregunta_tecnica"]


def test_contract_fields_present():
    """`autor`, `canal` and `texto` are read with their PDF names."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    m = batch.interacciones[0]
    assert m.autor == "Mariana Souza"
    assert m.canal == "#logros-y-empleos"
    assert m.texto.startswith("Comunidad, quede seleccionada")


def test_optional_fields_not_required():
    """The PDF example has no `id` or `timestamp`, so they must be optional."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    assert batch.interacciones[0].id is None
    assert batch.interacciones[0].timestamp is None


# ---------------------------------------------------------------------------
# OUTPUT tests
# ---------------------------------------------------------------------------

def test_output_validates_example():
    """The PDF output example must validate against OutputBatch."""
    out = OutputBatch(**SALIDA_EJEMPLO)
    assert out.status == "exito"
    assert out.resumen_comunidad.total_interacciones_procesadas == 2
    assert out.resumen_comunidad.sentimiento_predominante == "Altamente Positivo"
    assert out.activos_distribucion_generados.post_linkedin is not None
    assert out.almacenamiento_oci.status == "guardado_con_exito"


def test_output_exact_contract_keys():
    """The output top-level keys must be EXACTLY those of the PDF."""
    out = OutputBatch(**SALIDA_EJEMPLO)
    claves = set(out.model_dump().keys())
    assert claves == {
        "status",
        "resumen_comunidad",
        "activos_distribucion_generados",
        "almacenamiento_oci",
    }


# ---------------------------------------------------------------------------
# RESUMEN tests (HU-S4-009_PS / issue #113, Opción A)
# ---------------------------------------------------------------------------

def test_resumen_exact_contract_keys():
    """`resumen_comunidad` keys must be EXACTLY the documented contract.

    Additive fields are the intended way to extend the summary, so every
    addition has to be written here on purpose: a silent change of shape
    breaks whoever already consumes the contract, and an exact assertion is
    the only shape that notices. Add the field name here AND keep its default
    value, and the change stays backward compatible.
    """
    resumen = CommunitySummary(**SALIDA_EJEMPLO["resumen_comunidad"])
    claves = set(resumen.model_dump().keys())
    assert claves == {
        "total_interacciones_procesadas",
        "sentimiento_predominante",
        "temas_principales",
        "analisis_degradados",
        "feedback_negativo",
        "dudas_frecuentes",
        "tipos_discrepantes",
        # Opción A (HU-S4-003, issue #113)
        "distribucion_sentimiento",
        "temas_principales_conteo",
    }


def test_option_a_fields_stay_additive():
    """A payload written before Opción A must still validate unchanged.

    This is the retro-compatibility the issue requires: the two new fields
    carry `default_factory` values, so an old consumer that sends or stores
    only the original keys keeps working and gets empty containers back.
    """
    resumen_viejo = {
        clave: SALIDA_EJEMPLO["resumen_comunidad"][clave]
        for clave in (
            "total_interacciones_procesadas",
            "sentimiento_predominante",
            "temas_principales",
        )
    }
    resumen = CommunitySummary(**resumen_viejo)

    # The pre-existing fields are untouched.
    assert resumen.total_interacciones_procesadas == 2
    assert resumen.sentimiento_predominante == "Altamente Positivo"
    assert resumen.temas_principales == [
        "Contratacion / Logros",
        "LangGraph / Nodos Condicionales",
    ]
    # And the Opción A fields default to empty, never to None or an error.
    assert resumen.distribucion_sentimiento == {}
    assert resumen.temas_principales_conteo == []


def test_option_a_fields_accept_the_pipeline_shape():
    """The shape `_summarize` actually emits must validate and round-trip.

    `distribucion_sentimiento` is a plain dict keyed by the sentiment value;
    `temas_principales_conteo` is a list of `{tema, conteo}` objects.
    """
    resumen = CommunitySummary(
        **SALIDA_EJEMPLO["resumen_comunidad"],
        distribucion_sentimiento={"positivo": 1, "neutral": 1},
        temas_principales_conteo=[
            {"tema": "Contratacion / Logros", "conteo": 2},
            {"tema": "LangGraph / Nodos Condicionales", "conteo": 1},
        ],
    )

    assert resumen.distribucion_sentimiento == {"positivo": 1, "neutral": 1}
    assert [(tf.tema, tf.conteo) for tf in resumen.temas_principales_conteo] == [
        ("Contratacion / Logros", 2),
        ("LangGraph / Nodos Condicionales", 1),
    ]
    # Round-trips through JSON: the serialized summary carries both fields.
    payload = resumen.model_dump()
    assert payload["distribucion_sentimiento"] == {"positivo": 1, "neutral": 1}
    assert payload["temas_principales_conteo"][0] == {
        "tema": "Contratacion / Logros",
        "conteo": 2,
    }
