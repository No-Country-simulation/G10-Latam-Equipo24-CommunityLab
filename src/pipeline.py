"""End-to-end pipeline: input batch -> analysis -> decisions -> generators -> output.

This is the orchestrator (HU-S3-005). It receives a JSON file and produces the
contract OutputBatch.

Wiring:
    - analysis: real GeminiUnifiedAnalyzer (src/analysis).
    - decisions: real RuleBasedDecisionEngine (src/decisions), one instance for
      the whole batch.
    - generators: real per-channel generators (src/generators) mounted on the
      same LLM client instance, driven by the DECISIONS (not by the raw
      `tipo`). A generator failure degrades to a missing asset (None).
    - storage: OCI Object Storage (src/oci) when the SDK and the credentials
      are available; on any OCI failure it degrades to a local JSON snapshot
      under `storage/activos/` (working-directory relative).
"""
import logging
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TypeVar
from src.utils.topics import rank_topics

from dotenv import load_dotenv

from src.analysis.unified_analyzer import GeminiUnifiedAnalyzer
from src.decisions.engine import RECOGNIZED_TYPES, RuleBasedDecisionEngine
from src.domain.models import (
    ActionType,
    AnalysisComplete,
    AssetType,
    CommunitySummary,
    DecisionResult,
    DerivedMessage,
    DistributionAssets,
    FAQCandidate,
    InputBatch,
    InputMessage,
    LinkedInCandidate,
    OCIStorage,
    OutputBatch,
    SentimentType,
    TopicFrequency,
)
from src.generators.base import BaseGenerator
from src.generators.faq import FAQThemeGenerator, cluster_faq_targets
from src.generators.linkedin import LinkedInGenerator
from src.generators.newsletter import NewsletterGenerator
from src.ingest.loader import load_batch
from src.oci.client import OCIClient
from src.utils.llm import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

# Per-message triple consumed by _summarize/_generate.
_Result = Tuple[InputMessage, AnalysisComplete, DecisionResult]
# The (message, analysis) pair a generator needs.
_Target = Tuple[InputMessage, AnalysisComplete]

# Env vars that must be present (non-empty) before attempting an OCI upload.
_OCI_REQUIRED_ENV = (
    "OCI_USER_ID",
    "OCI_PRIVATE_KEY_PATH",
    "OCI_FINGERPRINT",
    "OCI_TENANCY_ID",
    "OCI_REGION",
)
_DEFAULT_BUCKET = "communitylab-activos-marketing"
_SNAPSHOT_DIR = Path("storage") / "activos"

# Maximum number of topics exposed in `temas_principales` (issue #87): the
# single place to change the cap.
_MAX_TOPICS = 5

# Option A (HU-S4-003): maximum number of topics exposed with their counts in
# `temas_principales_conteo`. The single place to change the cap.
_TOP_TOPICS_COUNTED = 10

# Presentation phrase for `sentimiento_predominante` (decision B, issue #87):
# the PDF example shows a phrase, not the raw enum value. The single place to
# change how a sentiment is presented; `SentimentType` itself is untouched.
_SENTIMENT_PHRASES = {
    SentimentType.POSITIVO: "Positivo",
    SentimentType.NEGATIVO: "Negativo",
    SentimentType.NEUTRO: "Neutro",
}

T = TypeVar("T")


def run_pipeline(source: str) -> OutputBatch:
    """Runs the full pipeline on a JSON file and returns the contract output."""
    # 0. Load environment variables from `.env` (if present) BEFORE any client
    # reads COMMUNITYLAB_LLM_BACKEND / *_API_KEY.
    load_dotenv()

    # 1. Ingest
    batch: InputBatch = load_batch(source)

    # 2-6. Analisis, decisiones, generadores y almacenamiento.
    return _run_with_batch(batch)


def _run_with_batch(batch: InputBatch) -> OutputBatch:
    """Corre el pipeline completo sobre un InputBatch ya cargado en memoria.

    Es el cuerpo post-ingesta de `run_pipeline`: el webhook de ingesta
    (src/ingest/webhook.py) arma el batch en memoria desde el request y lo
    pasa acá, sin escribir archivos temporales. El backend lo sigue decidiendo
    get_llm_client() a partir de COMMUNITYLAB_LLM_BACKEND.
    """
    # 2. LLM client (gemini / ollama / rule_based via COMMUNITYLAB_LLM_BACKEND)
    llm = get_llm_client()
    analyzer = GeminiUnifiedAnalyzer(client=llm)

    # 3-4. Analysis + decisions per message (one engine instance per batch)
    engine = RuleBasedDecisionEngine()
    results: List[_Result] = []
    for msg in batch.interacciones:
        analysis = analyzer.analyze(msg)             # real analysis (HU-S2-001)
        decision = engine.decide(msg, analysis)      # real rules (PR #84)
        results.append((msg, analysis, decision))

    # 5. Generators (real, driven by the decisions)
    assets = _generate(results, llm)

    # 6. Consolidate into the contract output
    return OutputBatch(
        status="exito",
        resumen_comunidad=_summarize(batch, results),
        activos_distribucion_generados=assets,
        almacenamiento_oci=_store(assets, batch),
    )


def _generate(results: List[_Result], llm: LLMClient) -> DistributionAssets:
    """Builds the distribution assets from the real decisions.

    Each channel is driven by the FIRST matching decision (never by `tipo`
    directly):
        - LinkedIn post  -> first PUBLISH + LINKEDIN decision.
        - Newsletter highlight -> the SAME message as the LinkedIn post when
          one exists, so the "logro de la semana" comes from the published
          testimonio and never from an earlier technical question; it falls
          back to the first interaction that is neither discarded nor derived
          to a human (a DERIVAR message is not a marketing asset).
        - FAQ suggestion -> first CREAR_FAQ decision.
        - FAQ candidates -> every CREAR_FAQ decision, listed only (no LLM call).
    A generator that returns None (LLM/JSON/validation failure) leaves its
    asset as None instead of failing the batch.
    """
    linkedin_gen = LinkedInGenerator(client=llm)
    newsletter_gen = NewsletterGenerator(client=llm)
    faq_gen = FAQThemeGenerator(client=llm)

    all_linkedin_targets = [
        (msg, analysis)
        for msg, analysis, decision in results
        if _is_linkedin_decision(decision)
    ]
    linkedin_target = all_linkedin_targets[0] if all_linkedin_targets else None
    newsletter_target = linkedin_target or _first_target(
        results,
        lambda d: d.action not in (ActionType.DESCARTAR, ActionType.DERIVAR),
    )

    # Published post and weekly highlight stay single assets (backward
    # compatible): the published post is the FIRST target, and the newsletter
    # comes from that same testimonio (falling back to the first interaction
    # that is neither discarded nor derived to a human).
    post_linkedin = _run(linkedin_gen, linkedin_target)
    destaque_newsletter = _run(newsletter_gen, newsletter_target)

    # Option A: one candidate per publishable testimonio, in batch order, so the
    # UI can offer a manual selector. "Grande": each candidate carries its FULL
    # post and its own newsletter highlight, so the selector swaps every field.
    # The FIRST target reuses the published post/highlight generated above, so
    # the first candidate can never diverge from the published copy (a
    # non-deterministic LLM would otherwise answer differently on a second
    # call).
    candidatos = []
    for index, (msg, analysis) in enumerate(all_linkedin_targets):
        if index == 0:
            post = post_linkedin
            newsletter = destaque_newsletter
        else:
            post = _run(linkedin_gen, (msg, analysis))
            newsletter = _run(newsletter_gen, (msg, analysis))
        if post is None:
            continue
        relevancia = (
            analysis.relevance.score if analysis.relevance is not None else 0.0
        )
        candidatos.append(
            LinkedInCandidate(
                autor=msg.autor,
                canal=msg.canal,
                texto_original=msg.texto,
                relevancia=relevancia,
                copy=post.copy,
                titulo=post.titulo,
                canal_recomendado=post.canal_recomendado,
                potencial_engagement=post.potencial_engagement,
                newsletter_seccion=newsletter.seccion if newsletter else "",
                newsletter_titular=newsletter.titular if newsletter else "",
                newsletter_resumen=newsletter.resumen if newsletter else "",
            )
        )

    # FAQ candidates: every CREAR_FAQ decision in batch order, listed with the
    # original question only. Topics are preserved for semantic clustering.
    candidatos_faq = [
        FAQCandidate(
            autor=msg.autor,
            canal=msg.canal,
            texto_original=msg.texto,
            relevancia=(
                analysis.relevance.score if analysis.relevance is not None else 0.0
            ),
            topics=(
                analysis.categorization.topics
                if analysis.categorization is not None
                else []
            ),
        )
        for msg, analysis, decision in results
        if decision.action == ActionType.CREAR_FAQ
    ]

    # FAQ semantic consolidation: group candidates into <=10 themes and generate
    # one tema+respuesta per cluster. The first theme stays the single published
    # suggestion (`sugerencia_contenido_faq`) for backward compatibility.
    faq_clusters = cluster_faq_targets(candidatos_faq)
    temas_faq = [
        theme
        for cluster in faq_clusters
        if (theme := faq_gen.generate_theme(cluster)) is not None
    ]
    sugerencia_contenido_faq = temas_faq[0] if temas_faq else None

    # Operator inbox: every DERIVAR decision becomes a DerivedMessage. The UI
    # cannot reconstruct this from the summary, so the pipeline materialises the
    # list explicitly (additive: old outputs default to an empty list).
    mensajes_derivados = [
        DerivedMessage(
            message_id=msg.id or decision.message_id,
            autor=msg.autor,
            canal=msg.canal,
            texto_original=msg.texto,
            razon=decision.reason,
            confianza=(
                analysis.sentiment.score if analysis.sentiment is not None else 0.0
            ),
        )
        for msg, analysis, decision in results
        if decision.action == ActionType.DERIVAR
    ]

    return DistributionAssets(
        post_linkedin=post_linkedin,
        destaque_newsletter_semanal=destaque_newsletter,
        sugerencia_contenido_faq=sugerencia_contenido_faq,
        candidatos_post_linkedin=candidatos,
        candidatos_faq=candidatos_faq,
        temas_faq=temas_faq,
        mensajes_derivados=mensajes_derivados,
    )


def _is_linkedin_decision(decision: DecisionResult) -> bool:
    """True for the decision that calls for a LinkedIn post."""
    return decision.action == ActionType.PUBLISH and decision.asset_type == AssetType.LINKEDIN


def _disagrees_with_llm_category(
    message: InputMessage, analysis: AnalysisComplete
) -> bool:
    """True when a recognized `tipo` disagrees with the LLM category (O-16).

    Only compared where both values are available: the engine's recognized
    `tipo` set (D-B) and a present categorization.
    """
    if message.tipo not in RECOGNIZED_TYPES:
        return False
    if analysis.categorization is None:
        return False
    return analysis.categorization.category != message.tipo


def _first_target(
    results: List[_Result], predicate: Callable[[DecisionResult], bool]
) -> Optional[_Target]:
    """Returns the (message, analysis) pair of the first matching decision."""
    for msg, analysis, decision in results:
        if predicate(decision):
            return msg, analysis
    return None


def _run(
    generator: BaseGenerator[T], target: Optional[_Target]
) -> Optional[T]:
    """Runs one generator on one target, degrading to None on failure."""
    if target is None:
        return None
    msg, analysis = target
    asset = generator.generate(msg, analysis)
    if asset is None:
        logger.warning(
            "Decided asset could not be generated: %s for autor=%r",
            type(generator).__name__,
            msg.autor,
        )
    return asset


def _ranked_topics(
    topics: List[str], top_n: int = _TOP_TOPICS_COUNTED
) -> List[TopicFrequency]:
    """Top topics ranked by frequency with their counts (Option A, HU-S4-003).

    Reuses `rank_topics` so `temas_principales` and `temas_principales_conteo`
    share normalization (plural singularization), the alphabetical tie-break
    and the ordering. Frequency descending; capped at `top_n`.
    """
    return [
        TopicFrequency(tema=topic, conteo=count)
        for topic, count in rank_topics(topics, top_n=top_n)
    ]


def _summarize(batch: InputBatch, results: List[_Result]) -> CommunitySummary:
    """Builds the community summary from the batch's analysis results."""
    sentiments = [
        analysis.sentiment.sentiment
        for _, analysis, _ in results
        if analysis.sentiment is not None
    ]
    # Option A (HU-S4-003): one Counter feeds both the predominant label and
    # the per-value distribution, so the two can never disagree. Every analyzed
    # message with a sentiment counts, including degraded fallbacks (NEUTRO).
    sentiment_counts = Counter(sentiments)
    predominant_value = (
        sentiment_counts.most_common(1)[0][0]
        if sentiments
        else SentimentType.NEUTRO
    )
    predominant = _SENTIMENT_PHRASES[predominant_value]
    distribucion_sentimiento = {
        sentiment.value: count
        for sentiment, count in sentiment_counts.items()
    }

    all_topics = [
        topic
        for _, analysis, _ in results
        if analysis.categorization is not None
        for topic in analysis.categorization.topics
    ]

    # Frequency descending; alphabetical tie-break; capped at _MAX_TOPICS.
    topics = [
        topic
        for topic, _ in rank_topics(all_topics, top_n=_MAX_TOPICS)
    ]

    # Option A (HU-S4-003): the same ranking, with counts, capped at 10.
    temas_principales_conteo = _ranked_topics(all_topics)

    # Analyses that fell back to the safe default because of an LLM failure
    # (issue #87): expose the count and log one aggregate warning.
    degraded = sum(1 for _, analysis, _ in results if analysis.is_degraded)
    if degraded > 0:
        logger.warning(
            "%d/%d interacciones degradadas al default",
            degraded,
            len(results),
        )

    # Negative feedback detected by sentiment analysis (decision D-F, #97):
    # expose how many messages expressed negative sentiment. This counts every
    # negative message, including low-confidence ones that fall through R4 and
    # are not routed to a human.
    feedback_negativo = sum(
        1
        for _, analysis, _ in results
        if analysis.sentiment is not None
        and analysis.sentiment.sentiment == SentimentType.NEGATIVO
    )

    # Technical questions routed to the FAQ rule (R2, CREAR_FAQ): the contract
    # only materializes ONE suggestion, but every matching decision is a FAQ
    # candidate asset. Count them for the assets-by-type summary.
    dudas_frecuentes = sum(
        1 for _, _, decision in results if decision.action == ActionType.CREAR_FAQ
    )

    # Risk O-16: measure how often a recognized `tipo` disagrees with the LLM
    # category. Measurement only: the engine keeps the `tipo` precedence (D-B)
    # untouched. One aggregate warning, like the degraded one above.
    tipos_discrepantes = sum(
        1
        for msg, analysis, _ in results
        if _disagrees_with_llm_category(msg, analysis)
    )
    if tipos_discrepantes > 0:
        logger.warning(
            "%d/%d interacciones con tipo y categoria del LLM discrepantes (O-16)",
            tipos_discrepantes,
            len(results),
        )

    return CommunitySummary(
        total_interacciones_procesadas=len(batch.interacciones),
        sentimiento_predominante=predominant,
        temas_principales=topics,
        analisis_degradados=degraded,
        feedback_negativo=feedback_negativo,
        dudas_frecuentes=dudas_frecuentes,
        tipos_discrepantes=tipos_discrepantes,
        distribucion_sentimiento=distribucion_sentimiento,
        temas_principales_conteo=temas_principales_conteo,
    )


def _store(assets: DistributionAssets, batch: InputBatch) -> OCIStorage:
    """Persists the asset package: OCI first, local snapshot as a fallback.

    Never raises on storage problems. If the `oci` SDK is missing, the OCI
    credentials are absent, or the upload fails, the assets are written to a
    local JSON snapshot (`storage/activos/paquete-distribucion-<date>.json`,
    relative to the working directory) and the record points at that path with
    `status="pendiente"`. A successful upload returns the contract status
    `status="guardado_con_exito"` and a period-scoped object key
    (`activos/<año>-semana-<n>/paquete-distribucion.json`, per the PDF).
    """
    bucket = os.getenv("OCI_BUCKET_NAME", _DEFAULT_BUCKET)
    today = date.today().isoformat()
    payload = assets.model_dump_json(indent=2)
    object_key = (
        f"activos/{_period_folder(batch.periodo_referencia)}/paquete-distribucion.json"
    )

    if _oci_credentials_present():
        try:
            oci_client = OCIClient()
            # Raises ImportError when the `oci` SDK is not installed.
            storage = oci_client.get_object_storage_client()
            storage.put_object(
                namespace_name=oci_client.namespace,
                bucket_name=bucket,
                object_name=object_key,
                put_object_body=payload.encode("utf-8"),
            )
            logger.info("Uploaded asset package to OCI: %s/%s", bucket, object_key)
            return OCIStorage(
                bucket=bucket, ruta_objeto=object_key, status="guardado_con_exito"
            )
        except Exception as exc:  # ImportError, SDK/network/auth errors, ...
            logger.warning(
                "OCI upload failed (%s); degrading to a local snapshot.", exc
            )
    else:
        logger.info(
            "OCI credentials not configured; writing a local snapshot instead."
        )

    snapshot = _SNAPSHOT_DIR / f"paquete-distribucion-{today}.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(payload, encoding="utf-8")
    logger.warning("Degraded storage: asset snapshot written to %s", snapshot)
    return OCIStorage(bucket=bucket, ruta_objeto=snapshot.as_posix(), status="pendiente")


def _period_folder(periodo_referencia: str) -> str:
    """Contract-shaped storage folder: `2026-semana-04`.

    Uses the week number from `periodo_referencia` when present (the input
    stamp "Semana_04", or "Semana_40_2026" for the Mastodon samples), falling
    back to today's ISO week, always with the current ISO year so the object
    path `activos/<año>-semana-<n>/...` matches the PDF example.
    """
    year, week, _ = date.today().isocalendar()
    match = re.search(r"(\d+)", periodo_referencia)
    number = match.group(1) if match else f"{week:02d}"
    return f"{year}-semana-{number}"


def _oci_credentials_present() -> bool:
    """True when every OCI credential env var is set to a non-empty value."""
    return all(os.getenv(name) for name in _OCI_REQUIRED_ENV)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample/messages.json"
    result = run_pipeline(path)
    print(result.model_dump_json(indent=2))
