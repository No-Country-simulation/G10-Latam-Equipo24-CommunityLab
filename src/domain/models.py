"""CommunityLab domain models.

IMPORTANT — these models mirror EXACTLY the data contract of the challenge
("Desafio 3 - CommunityLab"). The contract is documented in the README and
in docs/fuentes-de-datos.md.

Golden rule: do NOT add required fields that the PDF example does not have,
or the system will reject the grader's real input.

Convention: class names and comments are in English, but the FIELD names are
in Spanish because they are the exact JSON keys of the contract.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SentimentType(str, Enum):
    """Sentiment of a single message (internal analysis)."""
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutral"


class InteractionType(str, Enum):
    """Interaction types that come in the `tipo` field of the contract.

    The PDF explicitly shows `testimonio` and `pregunta_tecnica`.
    The rest are reasonable extensions. The decision engine must handle
    unknown values with a fallback, NOT crash.
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
# INPUT — contract (what the system receives)
# ---------------------------------------------------------------------------

class InputMessage(BaseModel):
    """A single interaction, exactly as it arrives in the contract.

    Required fields (present in the PDF example):
        autor   — person's name
        canal   — source channel (e.g. "#logros-y-empleos")
        tipo    — interaction type (e.g. "testimonio", "pregunta_tecnica")
        texto   — message content

    Optional fields (NOT in the PDF example; added for real data):
        id, timestamp, metadata.
    """
    autor: str
    canal: str
    tipo: str
    texto: str
    id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InputBatch(BaseModel):
    """The input envelope: a full batch of interactions."""
    origen_comunidad: str
    periodo_referencia: str
    interacciones: List[InputMessage]


# ---------------------------------------------------------------------------
# ANALYSIS — internal (intermediate pipeline results)
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
    """Consolidated analysis result for a single message."""
    message_id: str
    sentiment: Optional[SentimentResult] = None
    categorization: Optional[CategorizationResult] = None
    relevance: Optional[RelevanceResult] = None


# ---------------------------------------------------------------------------
# OUTPUT — contract (what the system produces)
# ---------------------------------------------------------------------------

class CommunitySummary(BaseModel):
    """Maps to the JSON key `resumen_comunidad`."""
    total_interacciones_procesadas: int
    sentimiento_predominante: str
    temas_principales: List[str] = Field(default_factory=list)


class LinkedInPost(BaseModel):
    """Maps to the JSON key `post_linkedin`."""
    titulo: str
    copy: str
    canal_recomendado: str = ""
    potencial_engagement: str = ""


class NewsletterHighlight(BaseModel):
    """Maps to the JSON key `destaque_newsletter_semanal`."""
    seccion: str
    titular: str
    resumen: str


class FAQSuggestion(BaseModel):
    """Maps to the JSON key `sugerencia_contenido_faq`."""
    tema: str
    origen: str = ""
    status: str = ""


class DistributionAssets(BaseModel):
    """Generated assets. Each is optional: not every batch produces all three."""
    post_linkedin: Optional[LinkedInPost] = None
    destaque_newsletter_semanal: Optional[NewsletterHighlight] = None
    sugerencia_contenido_faq: Optional[FAQSuggestion] = None


class OCIStorage(BaseModel):
    """Maps to the JSON key `almacenamiento_oci`."""
    bucket: str
    ruta_objeto: str
    status: str


class OutputBatch(BaseModel):
    """The full output the system must produce (contract).

    The top-level keys are EXACTLY those of the PDF:
    status, resumen_comunidad, activos_distribucion_generados, almacenamiento_oci.
    """
    status: str
    resumen_comunidad: CommunitySummary
    activos_distribucion_generados: DistributionAssets
    almacenamiento_oci: OCIStorage
