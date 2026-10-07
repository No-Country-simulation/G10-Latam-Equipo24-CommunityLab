from collections import defaultdict

from src.domain.models import (
    AnalysisComplete,
    InputMessage,
    RecurringTopic,
)


class RecurringTopicsDetector:
    """Detects recurring topics from unified analysis results."""

    def __init__(self, min_occurrences: int = 2):
        if min_occurrences < 2:
            raise ValueError("min_occurrences must be at least 2")

        self.min_occurrences = min_occurrences

    def detect(
        self,
        inputs: list[tuple[InputMessage, AnalysisComplete]],
    ) -> list[RecurringTopic]:
        """Detect recurring topics from unified analysis results."""
        if not isinstance(inputs, list):
            raise TypeError("inputs must be a list")

        topic_messages = defaultdict(list)

        for item in inputs:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError(
                    "each input must be a tuple of InputMessage and AnalysisComplete"
                )

            message, analysis = item

            if not isinstance(message, InputMessage):
                raise TypeError("input message must be an InputMessage")

            if not isinstance(analysis, AnalysisComplete):
                raise TypeError("analysis must be an AnalysisComplete")

            if analysis.categorization is None:
                continue

            topics = set(analysis.categorization.topics)

            for topic in topics:
                if topic:
                    topic_messages[topic].append(message.texto)

        results = []

        for topic, examples in topic_messages.items():
            count = len(examples)

            if count >= self.min_occurrences:
                results.append(
                    RecurringTopic(
                        topic=topic,
                        count=count,
                        examples=examples,
                        faq_title=self._suggest_faq_title(topic),
                    )
                )

        return sorted(results, key=lambda item: item.count, reverse=True)

    def _suggest_faq_title(self, topic: str) -> str:
        """Generate a simple FAQ title for a recurring topic."""
        return f"Preguntas frecuentes sobre {topic}"
