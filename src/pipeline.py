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
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TypeVar

from dotenv import load_dotenv

from src.analysis.unified_analyzer import GeminiUnifiedAnalyzer
from src.decisions.engine import RuleBasedDecisionEngine
from src.domain.models import (
    ActionType,
    AnalysisComplete,
    AssetType,
    CommunitySummary,
    DecisionResult,
    DistributionAssets,
    InputBatch,
    InputMessage,
    OCIStorage,
    OutputBatch,
)
from src.generators.base import BaseGenerator
from src.generators.faq import FAQGenerator
from src.generators.linkedin import LinkedInGenerator
from src.generators.newsletter import NewsletterGenerator
from src.ingest.input_loader import JSONInputLoader
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

T = TypeVar("T")


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
        almacenamiento_oci=_store(assets),
    )


def _generate(results: List[_Result], llm: LLMClient) -> DistributionAssets:
    """Builds the distribution assets from the real decisions.

    Each channel is driven by the FIRST matching decision (never by `tipo`
    directly):
        - LinkedIn post  -> first PUBLISH + LINKEDIN decision.
        - FAQ suggestion -> first CREAR_FAQ decision.
        - Newsletter highlight -> first non-discarded interaction: the
          newsletter is decoupled from LinkedIn and appears whenever there is
          any actionable interaction.
    A generator that returns None (LLM/JSON/validation failure) leaves its
    asset as None instead of failing the batch.
    """
    linkedin_gen = LinkedInGenerator(client=llm)
    newsletter_gen = NewsletterGenerator(client=llm)
    faq_gen = FAQGenerator(client=llm)

    linkedin_target = _first_target(results, _is_linkedin_decision)
    newsletter_target = _first_target(
        results, lambda d: d.action != ActionType.DESCARTAR
    )
    faq_target = _first_target(results, lambda d: d.action == ActionType.CREAR_FAQ)

    return DistributionAssets(
        post_linkedin=_run(linkedin_gen, linkedin_target),
        destaque_newsletter_semanal=_run(newsletter_gen, newsletter_target),
        sugerencia_contenido_faq=_run(faq_gen, faq_target),
    )


def _is_linkedin_decision(decision: DecisionResult) -> bool:
    """True for the decision that calls for a LinkedIn post."""
    return decision.action == ActionType.PUBLISH and decision.asset_type == AssetType.LINKEDIN


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


def _summarize(batch: InputBatch, results: List[_Result]) -> CommunitySummary:
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
    """Persists the asset package: OCI first, local snapshot as a fallback.

    Never raises on storage problems. If the `oci` SDK is missing, the OCI
    credentials are absent, or the upload fails, the assets are written to a
    local JSON snapshot (`storage/activos/paquete-distribucion-<date>.json`,
    relative to the working directory) and the record points at that path with
    `status="pendiente"`. A successful upload returns `status="subido"` and the
    object key.
    """
    bucket = os.getenv("OCI_BUCKET_NAME", _DEFAULT_BUCKET)
    today = date.today().isoformat()
    payload = assets.model_dump_json(indent=2)
    object_key = f"activos/paquete-distribucion-{today}.json"

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
            return OCIStorage(bucket=bucket, ruta_objeto=object_key, status="subido")
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
    return OCIStorage(bucket=bucket, ruta_objeto=str(snapshot), status="pendiente")


def _oci_credentials_present() -> bool:
    """True when every OCI credential env var is set to a non-empty value."""
    return all(os.getenv(name) for name in _OCI_REQUIRED_ENV)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample/messages.json"
    result = run_pipeline(path)
    print(result.model_dump_json(indent=2))
