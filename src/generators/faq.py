"""FAQ generator (sugerencia_contenido_faq)."""
from typing import Any, Dict, List

from src.domain.models import (
    AnalysisComplete,
    FAQCandidate,
    FAQSuggestion,
    InputMessage,
)
from src.generators.base import BaseGenerator
from src.prompts.generators import build_faq_theme_prompt
from src.utils.topics import _normalize_key, rank_topics

_STATUS = "generado"

# Synthetic delimiter used to carry a cluster's questions inside an InputMessage
# so the generator can reuse BaseGenerator's prompt/enrich/parse machinery.
_QUESTIONS_DELIMITER = "\n---\n"


def cluster_faq_targets(
    candidatos: List[FAQCandidate],
) -> tuple[List[List[FAQCandidate]], List[FAQCandidate]]:
    """Group FAQ candidates into at most 9 semantic themes.

    Returns ``(themes, orphaned)``: ``themes`` are the up-to-9 clusters with a
    clear, frequent topic; ``orphaned`` are the candidates without a clear
    topic plus any topic group beyond the 9th, so the UI can list them as
    "detected questions that did not map to a FAQ theme".
    """
    all_topics = [
        topic
        for c in candidatos
        for topic in (c.topics or [])
        if topic and topic.strip()
    ]
    ranked = rank_topics(all_topics, top_n=None)
    topic_priority = {label: idx for idx, (label, _) in enumerate(ranked)}

    clusters: Dict[str, List[FAQCandidate]] = {}
    untopiced: List[FAQCandidate] = []

    for c in candidatos:
        topics = [t for t in (c.topics or []) if t and t.strip()]
        if not topics:
            untopiced.append(c)
            continue

        # Pick the topic with the highest global frequency; ties are broken by
        # the normalized key so the choice is deterministic.
        chosen = min(
            topics,
            key=lambda t: (
                topic_priority.get(_normalize_key(t), float("inf")),
                _normalize_key(t),
            ),
        )
        key = _normalize_key(chosen)
        clusters.setdefault(key, []).append(c)

    # Sort by size descending, then normalized key for determinism.
    sorted_keys = sorted(clusters.keys(), key=lambda k: (-len(clusters[k]), k))
    groups = [clusters[k] for k in sorted_keys]

    # At most 9 explicit topic clusters become themes; group 10+ and untopiced
    # candidates are returned separately as orphaned, so no candidate is
    # dropped and the UI can list them apart from the themed FAQ entries.
    themes = groups[:9]
    orphaned = sum(groups[9:], []) + untopiced

    return themes, orphaned


class FAQThemeGenerator(BaseGenerator[FAQSuggestion]):
    """Generates one FAQ theme (tema + respuesta) from a cluster of questions.

    The LLM only produces `tema` and `respuesta`. The code owns the metadata:
    `origen` comes from the first candidate's channel, `status` is fixed, and
    `preguntas_relacionadas` lists the original questions in the cluster.
    """

    @property
    def output_model(self):
        return FAQSuggestion

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        """Build a theme prompt from an InputMessage carrying the questions."""
        questions = (
            message.texto.split(_QUESTIONS_DELIMITER)
            if message.texto
            else []
        )
        return build_faq_theme_prompt(questions)

    def generate_theme(
        self, candidates: List[FAQCandidate]
    ) -> FAQSuggestion | None:
        """Generate one FAQSuggestion for a cluster of related questions.

        Only the most representative question is surfaced (with the total
        count), so near-duplicate synthetic questions don't repeat in the UI.
        """
        if not candidates:
            return None

        questions = [c.texto_original for c in candidates if c.texto_original]
        if not questions:
            return None

        first = candidates[0]
        msg = InputMessage(
            autor=first.autor,
            canal=first.canal,
            tipo="pregunta_tecnica",
            texto=_QUESTIONS_DELIMITER.join(questions),
        )
        analysis = AnalysisComplete(message_id="theme")
        result = self._generate_from_prompt(
            build_faq_theme_prompt(questions), msg, analysis
        )
        if result is not None:
            result.pregunta_representativa = self._pick_representative(candidates)
            result.total_preguntas = len(questions)
        return result

    @staticmethod
    def _pick_representative(candidates: List[FAQCandidate]) -> str:
        """Pick the most representative question: highest relevance, ties
        broken by the shortest text (less noisy synthetic variants)."""
        with_text = [c for c in candidates if c.texto_original]
        if not with_text:
            return ""
        return max(
            with_text,
            key=lambda c: (c.relevancia, -len(c.texto_original)),
        ).texto_original

    def enrich(
        self,
        data: Dict[str, Any],
        message: InputMessage,
        analysis: AnalysisComplete,
    ) -> Dict[str, Any]:
        data["origen"] = message.canal or ""
        data["status"] = _STATUS
        return data
