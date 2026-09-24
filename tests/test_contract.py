"""Data contract tests — CommunityLab.

This file is THE safety net of the project: it verifies that the models accept
EXACTLY the input/output example of the challenge (PDF).

If this test fails, something broke the contract and it must NOT be merged.

Run from the repo root:
    python3 -m pytest tests/test_contract.py -q
"""
from src.domain.models import (
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
