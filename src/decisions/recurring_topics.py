from collections import defaultdict

from src.domain.models import (
    AnalysisComplete,
    InputMessage,
    RecurringTopic,
)
from src.utils.topics import rank_topics


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
            return []

        topic_messages = defaultdict(list)

        for item in inputs:
            if not isinstance(item, tuple) or len(item) != 2:
                continue

            message, analysis = item

            if not isinstance(message, InputMessage):
                continue

            if not isinstance(analysis, AnalysisComplete):
                continue

            if analysis.categorization is None:
                continue

            message_topics = rank_topics(
                analysis.categorization.topics,
                top_n=None,
            )

            for topic, _ in message_topics:
                topic_messages[topic].append(message.texto)

        all_topics = [
            topic
            for topic, examples in topic_messages.items()
            for _ in examples
        ]

        ranked_topics = rank_topics(
            all_topics,
            top_n=None,
        )

        results = []

        for topic, count in ranked_topics:
            if count >= self.min_occurrences:
                results.append(
                    RecurringTopic(
                        topic=topic,
                        count=count,
                        examples=topic_messages[topic],
                        faq_title=self._suggest_faq_title(topic),
                    )
                )

        return results

    def _suggest_faq_title(self, topic: str) -> str:
        """Generate a simple FAQ title for a recurring topic."""
        return f"Preguntas frecuentes sobre {topic}"
