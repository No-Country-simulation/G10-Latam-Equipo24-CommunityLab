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
    CREAR_FAQ = "crear_faq"
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


class RecurringTopic(BaseModel):
    """A recurring topic detected in community messages."""
    topic: str
    count: int
    examples: List[str] = Field(default_factory=list)
    faq_title: str


class TopicFrequency(BaseModel):
    """A topic ranked by frequency with its occurrence count (Option A)."""
    tema: str
    conteo: int


class AnalysisComplete(BaseModel):
    """Consolidated analysis result for a single message."""
    message_id: str
    sentiment: Optional[SentimentResult] = None
    categorization: Optional[CategorizationResult] = None
    relevance: Optional[RelevanceResult] = None
    # True ONLY when the safe default was caused by an LLM failure; an empty
    # message short-circuits before any LLM call and is not degraded (#87).
    is_degraded: bool = False


class DecisionResult(BaseModel):
    """Decision produced by the rule-based decision engine."""
    message_id: str
    action: ActionType
    asset_type: Optional[AssetType] = None
    reason: str


# ---------------------------------------------------------------------------
# OUTPUT — contract (what the system produces)
# ---------------------------------------------------------------------------

class CommunitySummary(BaseModel):
    """Maps to the JSON key `resumen_comunidad`."""
    total_interacciones_procesadas: int
    sentimiento_predominante: str
    temas_principales: List[str] = Field(default_factory=list)
    # How many analyses fell back to the safe default because of an LLM
    # failure (issue #87). Additive: OutputBatch top-level keys stay intact.
    analisis_degradados: int = 0
    # How many messages were routed to a human on negative feedback (rule R4,
    # decision D-F, issue #97). Additive: existing keys are unchanged.
    feedback_negativo: int = 0
    # How many messages triggered the FAQ suggestion rule (CREAR_FAQ). Additive:
    # the contract already exposes one suggestion; this counts the volume.
    dudas_frecuentes: int = 0
    # How often a recognized `tipo` disagreed with the LLM category (risk O-16).
    # Measurement only: routing precedence is unchanged. Additive via default.
    tipos_discrepantes: int = 0
    # Option A (HU-S4-003): counts per SentimentType value across the analyzed
    # batch. Keys are the sentiment values ("positivo", "negativo", "neutral").
    # Additive via default_factory: an empty batch yields {}.
    distribucion_sentimiento: Dict[str, int] = Field(default_factory=dict)
    # Option A (HU-S4-003): the top topics ranked by frequency with their
    # counts. Additive via default_factory: an empty batch yields [].
    temas_principales_conteo: List[TopicFrequency] = Field(default_factory=list)


class LinkedInPost(BaseModel):
    """Maps to the JSON key `post_linkedin`."""
    titulo: str
    copy: str
    canal_recomendado: str = ""
    potencial_engagement: str = ""


class LinkedInCandidate(BaseModel):
    """A publishable testimonio with its generated post (option A)."""
    autor: str = ""
    canal: str = ""
    texto_original: str = ""
    relevancia: float = 0.0
    copy: str = ""
    # Option A "grande": the full generated post, so the UI can swap every
    # field of the editor (not only the copy) when a candidate is selected.
    titulo: str = ""
    canal_recomendado: str = ""
    potencial_engagement: str = ""
    # Option A "grande": the weekly newsletter highlight derived from this same
    # testimonio, so the newsletter follows the selected publishable post.
    newsletter_seccion: str = ""
    newsletter_titular: str = ""
    newsletter_resumen: str = ""


class FAQCandidate(BaseModel):
    """A technical question routed by the FAQ rule, listed WITHOUT generated copy.

    Mirrors `LinkedInCandidate` but cheaper: the FAQ suggestion the contract
    materializes is a single asset, so the candidates only expose the original
    question and who asked it (no title/copy fields, no LLM call).
    """
    autor: str = ""
    canal: str = ""
    texto_original: str = ""
    relevancia: float = 0.0


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


class DerivedMessage(BaseModel):
    """A message routed to a human operator (decision DERIVAR).

    Additive output field: the operator inbox needs the original text, author,
    channel, reason and confidence so the UI can list and prioritise them.
    """
    message_id: str = ""
    autor: str = ""
    canal: str = ""
    texto_original: str = ""
    razon: str = ""
    confianza: float = 0.0


class DistributionAssets(BaseModel):
    """Generated assets. Each is optional: not every batch produces all three."""
    post_linkedin: Optional[LinkedInPost] = None
    destaque_newsletter_semanal: Optional[NewsletterHighlight] = None
    sugerencia_contenido_faq: Optional[FAQSuggestion] = None
    # Option A: every publishable testimonio with its LLM copy, so the UI can
    # offer a manual selector. Additive via default_factory: old outputs lack it.
    candidatos_post_linkedin: List[LinkedInCandidate] = Field(default_factory=list)
    # Every technical question routed by the FAQ rule (CREAR_FAQ), in batch
    # order, listed WITHOUT generated copy (no extra LLM call). Additive via
    # default_factory: old outputs lack it. The contract still materializes a
    # single `sugerencia_contenido_faq`.
    candidatos_faq: List[FAQCandidate] = Field(default_factory=list)
    # Messages routed to a human by DERIVAR decisions, surfaced in the operator
    # inbox. Additive via default_factory: old outputs lack it.
    mensajes_derivados: List[DerivedMessage] = Field(default_factory=list)


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
