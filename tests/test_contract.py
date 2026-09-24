"""Test del contrato de datos — CommunityLab.

Este archivo es LA red de seguridad del proyecto: verifica que los modelos
aceptan EXACTAMENTE el ejemplo de entrada/salida del desafío (PDF).

Si este test falla, algo rompió el contrato y NO se debe mergear.

Se ejecuta desde la raíz del repo:
    python3 -m pytest tests/test_contract.py -q
"""
from src.domain.models import (
    InputBatch,
    OutputBatch,
)

# ---------------------------------------------------------------------------
# El ejemplo LITERAL del PDF (Desafío 3 - CommunityLab)
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
# Tests de ENTRADA
# ---------------------------------------------------------------------------

def test_entrada_acepta_ejemplo_literal():
    """El ejemplo de entrada del PDF debe parsear SIN error de validación."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    assert batch.origen_comunidad == "Discord_Grupo_ONE_G10"
    assert batch.periodo_referencia == "Semana_04"
    assert len(batch.interacciones) == 2


def test_tipo_se_conserva():
    """El campo `tipo` NO se puede perder: es la señal del motor de decisiones."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    tipos = [i.tipo for i in batch.interacciones]
    assert tipos == ["testimonio", "pregunta_tecnica"]


def test_campos_del_contrato_presentes():
    """Los campos `autor`, `canal` y `texto` se leen con sus nombres del PDF."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    m = batch.interacciones[0]
    assert m.autor == "Mariana Souza"
    assert m.canal == "#logros-y-empleos"
    assert m.texto.startswith("Comunidad, quede seleccionada")


def test_campos_opcionales_no_son_obligatorios():
    """El ejemplo del PDF NO trae id ni timestamp → deben ser opcionales."""
    batch = InputBatch(**ENTRADA_EJEMPLO)
    assert batch.interacciones[0].id is None
    assert batch.interacciones[0].timestamp is None


# ---------------------------------------------------------------------------
# Tests de SALIDA
# ---------------------------------------------------------------------------

def test_salida_valida_contra_ejemplo():
    """El ejemplo de salida del PDF debe validar contra OutputBatch."""
    out = OutputBatch(**SALIDA_EJEMPLO)
    assert out.status == "exito"
    assert out.resumen_comunidad.total_interacciones_procesadas == 2
    assert out.resumen_comunidad.sentimiento_predominante == "Altamente Positivo"
    assert out.activos_distribucion_generados.post_linkedin is not None
    assert out.almacenamiento_oci.status == "guardado_con_exito"


def test_salida_claves_exactas_del_contrato():
    """Las claves top-level de la salida deben ser EXACTAMENTE las del PDF."""
    out = OutputBatch(**SALIDA_EJEMPLO)
    claves = set(out.model_dump().keys())
    assert claves == {
        "status",
        "resumen_comunidad",
        "activos_distribucion_generados",
        "almacenamiento_oci",
    }
