"""JSON input loader for CommunityLab."""
import json
from pathlib import Path
from typing import List
from src.domain.models import InputMessage


class JSONInputLoader:
    def load(self, source: str) -> List[InputMessage]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "interactions" not in data:
            raise ValueError("Invalid JSON format")
        interactions = []
        for msg in data["interactions"]:
            interactions.append(InputMessage(**msg))
        return interactions
