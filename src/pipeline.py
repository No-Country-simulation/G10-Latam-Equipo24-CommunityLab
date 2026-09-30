"""End-to-end pipeline: input batch -> analysis -> decisions -> generators -> output.

This is the orchestrator (HU-S3-005). It receives a JSON file and produces the
contract OutputBatch.

NOTE: the decisions and generators steps are STUBS for now. The analysis step
already uses the real GeminiUnifiedAnalyzer (src/analysis).
"""
from collections import Counter

from dotenv import load_dotenv

from src.domain.models import (
    AnalysisComplete,
    CommunitySummary,
    DistributionAssets,
    FAQSuggestion,
    InputBatch,
    InputMessage,
    LinkedInPost,
    NewsletterHighlight,
    OCIStorage,
    OutputBatch,
)
from src.analysis.unified_analyzer import GeminiUnifiedAnalyzer
from src.ingest.input_loader import JSONInputLoader
from src.ingest.normalizer import InputNormalizer
from src.utils.llm import get_llm_client


def run_pipeline(source: str) -> OutputBatch:
    """Runs the full pipeline on a JSON file and returns the contract output."""
    # 0. Load environment variables from `.env` (if present) BEFORE any client
    # reads COMMUNITYLAB_LLM_BACKEND / *_API_KEY.
    load_dotenv()

    # 1. Ingest
    batch: InputBatch = JSONInputLoader().load_batch(source)

    # 2. LLM client (gemini / ollama / rule_based via COMMUNITYLAB_LLM_BACKEND)
    llm = get_llm_client()
    analyzer = GeminiUnifiedAnalyzer(client=llm)

    # 3-4. Analysis + decisions per message
    results = []
    for msg in batch.interacciones:
        analysis = analyzer.analyze(msg)       # real analysis (HU-S2-001)
        decision = _decide(msg, analysis)      # STUB (routes by `tipo`)
        results.append((msg, analysis, decision))

    # 5. Generators
    assets = _generate(results, llm)           # STUB

    # 6. Consolidate into the contract output
    return OutputBatch(
        status="exito",
        resumen_comunidad=_summarize(batch, results),
        activos_distribucion_generados=assets,
        almacenamiento_oci=_store(assets),
    )


# ---------------------------------------------------------------------------
# STUBS — to be replaced by the real src/decisions and src/generators modules.
# ---------------------------------------------------------------------------

def _decide(msg: InputMessage, analysis: AnalysisComplete) -> str:
    """STUB: routes by `tipo` (the contract's key signal).

    TODO: replace with the real decision engine.
    """
    # `tipo` normalization lives in ONE place: InputNormalizer.normalize_tipo.
    tipo = InputNormalizer.normalize_tipo(msg.tipo)
    if tipo == "testimonio":
        return "post_linkedin"
    if tipo == "pregunta_tecnica":
        return "faq"
    return "descartar"


def _generate(results, llm) -> DistributionAssets:
    """STUB: builds placeholder assets from the decisions.

    TODO: replace with the real generators that call `llm.generate(...)` with
    the per-channel prompts (src/prompts).
    """
    has_linkedin = any(d == "post_linkedin" for _, _, d in results)
    has_faq = any(d == "faq" for _, _, d in results)
    # The newsletter highlight is decoupled from LinkedIn: it appears whenever
    # there is any non-discarded interaction (testimonio OR pregunta). The real
    # criterion (e.g. engagement) will replace this placeholder later.
    has_newsletter_content = any(d != "descartar" for _, _, d in results)

    return DistributionAssets(
        post_linkedin=(
            LinkedInPost(
                titulo="Placeholder title",
                copy="Placeholder LinkedIn copy.",
                canal_recomendado="LinkedIn Oficial",
                potencial_engagement="Medio",
            )
            if has_linkedin
            else None
        ),
        destaque_newsletter_semanal=(
            NewsletterHighlight(
                seccion="Logro de la Semana",
                titular="Placeholder highlight",
                resumen="Placeholder newsletter summary.",
            )
            if has_newsletter_content
            else None
        ),
        sugerencia_contenido_faq=(
            FAQSuggestion(
                tema="Placeholder FAQ topic",
                origen="Placeholder origin",
                status="derivado_a_mentoria",
            )
            if has_faq
            else None
        ),
    )


def _summarize(batch: InputBatch, results) -> CommunitySummary:
    """Builds the community summary from the batch's analysis results."""
    sentiments = [
        analysis.sentiment.sentiment.value
        for _, analysis, _ in results
        if analysis.sentiment is not None
    ]
    predominant = (
        Counter(sentiments).most_common(1)[0][0] if sentiments else "neutral"
    )

    topics = sorted({
        topic
        for _, analysis, _ in results
        if analysis.categorization is not None
        for topic in analysis.categorization.topics
    })

    return CommunitySummary(
        total_interacciones_procesadas=len(batch.interacciones),
        sentimiento_predominante=predominant,
        temas_principales=topics,
    )


def _store(assets: DistributionAssets) -> OCIStorage:
    """STUB: returns a placeholder storage record.

    TODO: replace with the real OCI Object Storage integration (src/oci).
    """
    return OCIStorage(
        bucket="communitylab-activos-marketing",
        ruta_objeto="activos/demo/paquete-distribucion.json",
        status="pendiente",
    )


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample/messages.json"
    result = run_pipeline(path)
    print(result.model_dump_json(indent=2))
