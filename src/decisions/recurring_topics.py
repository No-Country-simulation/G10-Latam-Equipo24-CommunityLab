from collections import Counter, defaultdict
import re
import unicodedata

from src.domain.models import RecurringTopic


class RecurringTopicsDetector:
    """Detects recurring topics in community messages."""

    STOPWORDS = {
        "como", "cómo", "que", "qué", "donde", "dónde", "cuando", "cuándo",
        "puedo", "puede", "pueden", "para", "por", "una", "uno", "unos",
        "unas", "los", "las", "del", "con", "sin", "sobre", "esta", "este",
        "esto", "hay", "tengo", "tiene", "tienen", "quiero", "necesito",
        "me", "mi", "mis", "el", "la", "de", "en", "y", "o", "un",
        "cambiar", "cambio", "cambie", "cambias", "cambia", "cambian",
        "actualizar", "actualizo", "actualiza", "actualice", "actualizas",
        "actualizan", "hacer", "hago", "hace", "haces", "hacen",
        "acceder", "acceso", "entrar", "entro", "entra", "entran",
        "funciona", "funcion", "funcionan", "funciono",
        "problema", "problemas", "ayuda",
    }

    def __init__(self, min_occurrences: int = 2):
        if min_occurrences < 2:
            raise ValueError("min_occurrences must be at least 2")

        self.min_occurrences = min_occurrences

    def detect(self, messages: list[str]) -> list[RecurringTopic]:
        """Detect recurring topics and return FAQ-ready information."""
        topic_messages = defaultdict(list)
        topic_labels = defaultdict(Counter)

        for message in messages:
            topic, grouping_key = self._extract_topic(message)

            if topic:
                topic_messages[grouping_key].append(message)
                topic_labels[grouping_key][topic] += 1

        results = []

        for grouping_key, examples in topic_messages.items():
            count = len(examples)

            if count >= self.min_occurrences:
                topic = topic_labels[grouping_key].most_common(1)[0][0]

                results.append(
                    RecurringTopic(
                        topic=topic,
                        count=count,
                        examples=examples,
                        faq_title=self._suggest_faq_title(topic),
                    )
                )

        return sorted(results, key=lambda item: item.count, reverse=True)

    def _normalize_word(self, word: str) -> str:
        """Normalize common Spanish plural forms to singular."""
        if word.endswith("iones") and len(word) > 6:
            return word[:-5] + "ión"

        if word.endswith("s") and len(word) > 4:
            singular_candidate = word[:-1]

            if singular_candidate[-1] in "aeiouáéíóúü":
                return singular_candidate

        if word.endswith("es") and len(word) > 5:
            return word[:-2]

        return word

    def _grouping_key(self, word: str) -> str:
        """Create an accent-insensitive key for grouping topics."""
        normalized = unicodedata.normalize("NFD", word)

        return "".join(
            char
            for char in normalized
            if unicodedata.category(char) != "Mn"
        )

    def _extract_topic(self, message: str) -> tuple[str, str] | tuple[None, None]:
        """Extract a display topic and grouping key from a message."""
        words = re.findall(
            r"[a-záéíóúüñ]+",
            message.lower(),
        )

        meaningful_words = [
            self._normalize_word(word)
            for word in words
            if word not in self.STOPWORDS and len(word) > 2
        ]

        if not meaningful_words:
            return None, None

        word_counts = Counter(meaningful_words)
        topic = word_counts.most_common(1)[0][0]

        return topic, self._grouping_key(topic)

    def _suggest_faq_title(self, topic: str) -> str:
        """Generate a simple FAQ title for a recurring topic."""
        return f"Preguntas frecuentes sobre {topic}"