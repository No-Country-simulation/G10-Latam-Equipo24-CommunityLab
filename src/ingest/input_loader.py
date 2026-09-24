"""JSON input loader for CommunityLab."""
import json
from pathlib import Path
from typing import List

from src.domain.models import InputBatch, InputMessage


class JSONInputLoader:
    """Loads a batch of interactions from a JSON file (contract format).

    Expected format (contract):
    {
      "origen_comunidad": "...",
      "periodo_referencia": "...",
      "interacciones": [ { "autor", "canal", "tipo", "texto" } ]
    }
    """

    def load(self, source: str) -> List[InputMessage]:
        """Returns the list of interactions (compatible with DataLoader)."""
        return self.load_batch(source).interacciones

    def load_batch(self, source: str) -> InputBatch:
        """Returns the full batch (InputBatch), preserving the envelope."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON format: expected an object")

        # The contract uses "interacciones" (Spanish). We tolerate "interactions".
        if "interacciones" not in data:
            if "interactions" in data:
                data = {**data, "interacciones": data.pop("interactions")}
            else:
                raise ValueError("Invalid JSON format: missing 'interacciones' key")

        return InputBatch(**data)
