"""Modelos de dominio de CommunityLab.

IMPORTANTE — estos modelos reflejan EXACTAMENTE el contrato de datos del
desafío (Desafío 3 - CommunityLab). El contrato está documentado en el README
y en docs/contract.md.

Regla de oro: NO agregues campos obligatorios que el ejemplo del PDF no tenga,
porque entonces el sistema rechazará la entrada real del jurado.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SentimentType(str, Enum):
    """Sentimiento de un mensaje individual (análisis interno)."""
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutral"


class InteractionType(str, Enum):
    """Tipos de interacción que vienen en el campo `tipo` del contrato.

    El PDF muestra explícitamente `testimonio` y `pregunta_tecnica`.
    El resto son extensiones razonables. El motor de decisiones debe manejar
    un valor desconocido con un fallback, NO reventar.
    """
    TESTIMONIO = "testimonio"
    PREGUNTA_TECNICA = "pregunta_tecnica"
    FEEDBACK = "feedback"
    LOGRO = "logro"
    DISCUSION = "discusion"
    OTRO = "otro"


class AssetType(str, Enum):
    LINKEDIN = "linkedin"
    NEWSLETTER = "newsletter"
    FAQ = "faq"
    TESTIMONIAL = "testimonial"


class RiskLevel(str, Enum):
    INFO = "info"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


class ActionType(str, Enum):
    PUBLISH = "publicar"
    DERIVAR = "derivar"
    DESCARTAR = "descartar"


# ---------------------------------------------------------------------------
# ENTRADA — contrato (lo que el sistema recibe)
# ---------------------------------------------------------------------------

class InputMessage(BaseModel):
    """Una interacción individual, tal como llega en el contrato.

    Campos OBLIGATORIOS (vienen en el ejemplo del PDF):
        autor   — nombre de la persona
        canal   — canal de origen (ej. "#logros-y-empleos")
        tipo    — tipo de interacción (ej. "testimonio", "pregunta_tecnica")
        texto   — contenido del mensaje

    Campos OPCIONALES (NO están en el ejemplo del PDF; se agregan para
    soportar datos reales): id, timestamp, metadata.
    """
    autor: str
    canal: str
    tipo: str
    texto: str
    id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InputBatch(BaseModel):
    """El sobre (envelope) de entrada: un lote completo de interacciones."""
    origen_comunidad: str
    periodo_referencia: str
    interacciones: List[InputMessage]


# ---------------------------------------------------------------------------
# ANÁLISIS — interno (resultados intermedios del pipeline)
# ---------------------------------------------------------------------------

class SentimentResult(BaseModel):
    message_id: str
    sentiment: SentimentType
    score: float
    reasoning: str = ""


class CategorizationResult(BaseModel):
    message_id: str
    category: str
    topics: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)


class RelevanceResult(BaseModel):
    message_id: str
    score: float
    is_marketing_worthy: bool


class AnalysisComplete(BaseModel):
    """Resultado consolidado del análisis de un mensaje."""
    message_id: str
    sentiment: Optional[SentimentResult] = None
    categorization: Optional[CategorizationResult] = None
    relevance: Optional[RelevanceResult] = None


# ---------------------------------------------------------------------------
# SALIDA — contrato (lo que el sistema produce)
# ---------------------------------------------------------------------------

class ResumenComunidad(BaseModel):
    total_interacciones_procesadas: int
    sentimiento_predominante: str
    temas_principales: List[str] = Field(default_factory=list)


class PostLinkedIn(BaseModel):
    titulo: str
    copy: str
    canal_recomendado: str = ""
    potencial_engagement: str = ""


class DestaqueNewsletter(BaseModel):
    seccion: str
    titular: str
    resumen: str


class SugerenciaFAQ(BaseModel):
    tema: str
    origen: str = ""
    status: str = ""


class ActivosDistribucion(BaseModel):
    """Activos generados. Cada uno es opcional porque no todo lote produce
    los tres tipos (ej. un lote sin dudas no genera FAQ)."""
    post_linkedin: Optional[PostLinkedIn] = None
    destaque_newsletter_semanal: Optional[DestaqueNewsletter] = None
    sugerencia_contenido_faq: Optional[SugerenciaFAQ] = None


class AlmacenamientoOCI(BaseModel):
    bucket: str
    ruta_objeto: str
    status: str


class OutputBatch(BaseModel):
    """La salida completa que el sistema debe producir (contrato).

    Las claves top-level son EXACTAMENTE las del PDF:
    status, resumen_comunidad, activos_distribucion_generados, almacenamiento_oci.
    """
    status: str
    resumen_comunidad: ResumenComunidad
    activos_distribucion_generados: ActivosDistribucion
    almacenamiento_oci: AlmacenamientoOCI
