"""Normalizer for raw input messages."""
import uuid
from src.domain.models import InputMessage


class InputNormalizer:
    def normalize(self, source: str, raw: dict) -> InputMessage:
        """Convert a raw message from any source into a normalized InputMessage."""
        return InputMessage(
            id=raw.get("id") or uuid.uuid4().hex,
            content=raw.get("content", ""),
            author=raw.get("author", ""),
            channel=raw.get("channel", f"#{source}"),
            timestamp=raw.get("timestamp", ""),
            metadata={
                "reactions": raw.get("reactions", 0),
                "attachments": raw.get("attachments", 0),
            },
        )
