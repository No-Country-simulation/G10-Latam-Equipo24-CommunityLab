"""JSON input loader for CommunityLab."""
import json
from pathlib import Path
from typing import List

from src.domain.models import InputBatch, InputMessage


class JSONInputLoader:
    """Carga un lote de interacciones desde un JSON con el formato del contrato.

    Formato esperado (contrato del desafío):
    {
      "origen_comunidad": "...",
      "periodo_referencia": "...",
      "interacciones": [ { "autor", "canal", "tipo", "texto" } ]
    }
    """

    def load(self, source: str) -> List[InputMessage]:
        """Devuelve la lista de interacciones (compatible con DataLoader)."""
        return self.load_batch(source).interacciones

    def load_batch(self, source: str) -> InputBatch:
        """Devuelve el lote completo (InputBatch), preservando el sobre."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON format: expected an object")

        # El contrato usa "interacciones" (español). Toleramos "interactions".
        if "interacciones" not in data:
            if "interactions" in data:
                data = {**data, "interacciones": data.pop("interactions")}
            else:
                raise ValueError("Invalid JSON format: missing 'interacciones' key")

        return InputBatch(**data)
