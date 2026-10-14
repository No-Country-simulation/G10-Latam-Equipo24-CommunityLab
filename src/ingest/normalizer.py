"""Normalizer: converts raw data from any source into the contract."""
from typing import Any, Dict, Optional

from src.domain.models import InputMessage


class InputNormalizer:
    """Converts a raw message into a contract InputMessage.

    Accepts both the contract field names (autor/canal/tipo/texto) and the
    English alternatives (author/channel/content), and normalizes `tipo` to the
    canonical form (lowercase, spaces replaced by underscores).
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
            autor=self.normalize_autor(raw.get("autor") or raw.get("author")),
            canal=raw.get("canal") or raw.get("channel") or f"#{source}",
            tipo=tipo or self.normalize_tipo(raw.get("tipo")),
            texto=raw.get("texto") or raw.get("content") or "",
            id=raw.get("id"),
            timestamp=raw.get("timestamp") or raw.get("fecha"),
            metadata=metadata,
        )

    @staticmethod
    def normalize_autor(raw_autor: Optional[str]) -> str:
        """Cleans a raw author into a display-safe name.

        Mastodon hands the account ``acct`` as ``user@instance``: a platform
        handle, not a person's name. ``flowfx@chaos.social`` becomes
        ``flowfx`` so the dashboard never shows a raw handle. Authors without a
        handle (already display-safe) are returned untouched.
        """
        if not raw_autor:
            return ""
        autor = str(raw_autor).strip()
        if "@" not in autor:
            return autor
        local = autor.lstrip("@").split("@", 1)[0].strip()
        return local or autor

    @staticmethod
    def normalize_tipo(raw_tipo: Optional[str]) -> str:
        """Normalizes a raw `tipo` value to the canonical form.

        Example: "pregunta tecnica" -> "pregunta_tecnica",
        "Comentario General" -> "comentario_general".

        Empty, None, or whitespace-only values fall back to "otro".
        """
        if not raw_tipo:
            return "otro"
        normalized = str(raw_tipo).strip().lower().replace(" ", "_")
        return normalized or "otro"
