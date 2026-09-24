"""Normalizer: convierte datos crudos de cualquier fuente al contrato."""
from typing import Any, Dict, Optional

from src.domain.models import InputMessage


class InputNormalizer:
    """Convierte un mensaje crudo en un InputMessage del contrato.

    Acepta tanto los nombres del contrato (autor/canal/tipo/texto) como los
    alternativos en inglés (author/channel/content), y deriva `tipo` cuando la
    fuente no lo trae explícito.
    """

    def normalize(
        self,
        source: str,
        raw: Dict[str, Any],
        tipo: Optional[str] = None,
    ) -> InputMessage:
        metadata = dict(raw.get("metadata") or {})
        if "url" in raw:
            metadata["url"] = raw["url"]

        return InputMessage(
            autor=raw.get("autor") or raw.get("author") or "",
            canal=raw.get("canal") or raw.get("channel") or f"#{source}",
            tipo=tipo or raw.get("tipo") or "otro",
            texto=raw.get("texto") or raw.get("content") or "",
            id=raw.get("id"),
            timestamp=raw.get("timestamp") or raw.get("fecha"),
            metadata=metadata,
        )
