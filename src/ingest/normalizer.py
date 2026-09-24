"""Normalizer: converts raw data from any source into the contract."""
from typing import Any, Dict, Optional

from src.domain.models import InputMessage


class InputNormalizer:
    """Converts a raw message into a contract InputMessage.

    Accepts both the contract field names (autor/canal/tipo/texto) and the
    English alternatives (author/channel/content), and derives `tipo` when the
    source does not provide it explicitly.
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
