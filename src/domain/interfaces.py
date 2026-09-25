"""Domain interfaces for CommunityLab."""
from abc import ABC, abstractmethod
from typing import List, Dict
from src.domain.models import (
    InputMessage,
    SentimentResult,
    CategorizationResult,
    RelevanceResult,
)


class DataLoader(ABC):
    @abstractmethod
    def load(self, source: str) -> List[InputMessage]:
        pass


class SentimentAnalyzer(ABC):
    @abstractmethod
    def analyze(self, message: InputMessage) -> SentimentResult:
        pass


class Categorizer(ABC):
    @abstractmethod
    def categorize(self, message: InputMessage) -> CategorizationResult:
        pass


class RelevanceScorer(ABC):
    @abstractmethod
    def score(self, message: InputMessage) -> RelevanceResult:
        pass


class DecisionEngine(ABC):
    @abstractmethod
    def decide(self, analysis: List[InputMessage]) -> List[Dict]:
        pass


class AssetGenerator(ABC):
    @abstractmethod
    def generate(self, asset_type: str, context: Dict) -> Dict:
        pass


class StorageClient(ABC):
    @abstractmethod
    def upload(self, key: str, data: Dict) -> bool:
        pass

    @abstractmethod
    def download(self, key: str) -> Dict:
        pass
