from collections import Counter, defaultdict
import re


class RecurringTopicsDetector:
    """Detects recurring topics in community messages."""

    STOPWORDS = {
        "como", "cómo", "que", "qué", "donde", "dónde", "cuando", "cuándo",
        "puedo", "puede", "pueden", "para", "por", "una", "uno", "unos",
        "unas", "los", "las", "del", "con", "sin", "sobre", "esta", "este",
        "esto", "hay", "tengo", "tiene", "tienen", "quiero", "necesito",
        "me", "mi", "mis", "el", "la", "de", "en", "y", "o", "un",
        "cambiar", "cambio", "cambie", "cambias", "actualizar", "actualizo",
        "actualiza", "actualice", "hacer", "hago", "hace",
        "acceder", "acceso", "entrar", "entro", "funciona", "funcion",
        "problema", "ayuda",
    }

    def __init__(self, min_occurrences: int = 2):
        if min_occurrences < 2:
            raise ValueError("min_occurrences must be at least 2")

        self.min_occurrences = min_occurrences

    def detect(self, messages: list[str]) -> list[dict]:
        """Detect recurring topics and return FAQ-ready information."""
        topic_messages = defaultdict(list)

        for message in messages:
            topic = self._extract_topic(message)

            if topic:
                topic_messages[topic].append(message)

        results = []

        for topic, examples in topic_messages.items():
            count = len(examples)

            if count >= self.min_occurrences:
                results.append(
                    {
                        "topic": topic,
                        "count": count,
                        "examples": examples,
                        "faq_title": self._suggest_faq_title(topic),
                    }
                )

        return sorted(results, key=lambda item: item["count"], reverse=True)

    def _extract_topic(self, message: str) -> str | None:
        """Extract a topic from the most relevant word in a message."""
        words = re.findall(
            r"[a-záéíóúüñ]+",
            message.lower(),
        )

        meaningful_words = [
            word
            for word in words
            if word not in self.STOPWORDS and len(word) > 2
        ]

        if not meaningful_words:
            return None

        word_counts = Counter(meaningful_words)

        return word_counts.most_common(1)[0][0]

    def _suggest_faq_title(self, topic: str) -> str:
        """Generate a simple FAQ title for a recurring topic."""
        return f"Preguntas frecuentes sobre {topic}"
