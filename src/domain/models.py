"""Domain models for CommunityLab."""
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SentimentType(str, Enum):
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutral"


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


class InputMessage(BaseModel):
    id: str
    content: str
    author: str
    channel: str
    timestamp: str
    metadata: Dict[str, Any] = {}


class SentimentResult(BaseModel):
    message_id: str
    sentiment: SentimentType
    score: float
    reasoning: str


class CategorizationResult(BaseModel):
    message_id: str
    category: str
    topics: List[str]
    entities: List[str]


class RelevanceResult(BaseModel):
    message_id: str
    score: float
    is_marketing_worthy: bool


class AnalysisComplete(BaseModel):
    message_id: str
    sentiment: Optional[SentimentResult] = None
    categorization: Optional[CategorizationResult] = None
    relevance: Optional[RelevanceResult] = None


class OutputBatch(BaseModel):
    batch_id: str
    processed_at: str
    summary: Dict[str, Any]
    analysis: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    assets: List[Dict[str, Any]]
    oci_storage: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    visualization: Dict[str, Any]
