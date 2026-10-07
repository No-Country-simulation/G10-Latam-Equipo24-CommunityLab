"""End-to-end pipeline tests (HU-S3-005).

Runs the full pipeline (real analyzer wiring, real decision engine, real
generators and real storage step) against a FAKE LLM client, so no API key is
needed and CI stays deterministic. The fake returns canned JSON matching each
generator's `output_model`.

The storage step is isolated in `tmp_path`: without OCI credentials the
pipeline degrades to a local JSON snapshot, and the autouse fixture changes the
working directory so those snapshots never land in the repository.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from src.domain.models import OutputBatch
from src.pipeline import run_pipeline
from src.utils.llm import LLMClient

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "pipeline_sample.json"

# Marker inside a message text: the fake analyzer answers `negativo` for it.
NEGATIVE_MARKER = "[sentimiento negativo]"

_ANALYSIS_PAYLOAD = {
    "sentiment": {"type": "positivo", "score": 0.9, "reasoning": "fake analysis"},
    "categorization": {"category": "otro", "topics": ["fake"], "entities": []},
    "relevance": {"score": 0.9},
}
_LINKEDIN_PAYLOAD = {
    "titulo": "Titulo generado",
    "copy": "Copy generado",
    "canal_recomendado": "LinkedIn Oficial",
    "potencial_engagement": "Alto",
}
_NEWSLETTER_PAYLOAD = {
    "seccion": "Logro de la Semana",
    "titular": "Titular generado",
    "resumen": "Resumen generado",
}
_FAQ_PAYLOAD = {"tema": "Tema generado"}


class FakeLLMClient(LLMClient):
    """Deterministic fake LLM: routes on the prompt type.

    Analysis prompts (src/prompts/templates) get a positive and relevant
    analysis, unless the message text carries `NEGATIVE_MARKER`. Generator
    prompts (src/prompts/generators) get the canned JSON for their channel.
    """

    def generate(self, prompt: str, **kwargs) -> str:
        if "sentiment.type" in prompt:
            payload = dict(_ANALYSIS_PAYLOAD)
            if NEGATIVE_MARKER in prompt:
                payload["sentiment"] = {
                    "type": "negativo",
                    "score": 0.9,
                    "reasoning": "fake analysis",
                }
            return json.dumps(payload)
        if "post de LinkedIn" in prompt:
            return json.dumps(_LINKEDIN_PAYLOAD)
        if "destaque de newsletter semanal" in prompt:
            return json.dumps(_NEWSLETTER_PAYLOAD)
        if "TEMA de una FAQ" in prompt:
            return json.dumps(_FAQ_PAYLOAD)
        raise AssertionError(f"FakeLLMClient got an unexpected prompt: {prompt[:120]!r}")


@pytest.fixture(autouse=True)
def pipeline_env(monkeypatch, tmp_path):
    """Fake the LLM client and isolate the storage step.

    - `src.pipeline.get_llm_client` -> FakeLLMClient (no API key, deterministic).
    - cwd -> tmp_path, so the local snapshot fallback writes outside the repo.
    - OCI credentials are removed, so storage always degrades locally.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.pipeline.get_llm_client", lambda: FakeLLMClient())
    for var in (
        "OCI_USER_ID",
        "OCI_PRIVATE_KEY_PATH",
        "OCI_FINGERPRINT",
        "OCI_TENANCY_ID",
        "OCI_REGION",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _write_batch(tmp_path, interacciones, name="batch.json") -> str:
    """Writes a minimal contract batch to `tmp_path` and returns its path."""
    batch = {
        "origen_comunidad": "test",
        "periodo_referencia": "Semana_05",
        "interacciones": interacciones,
    }
    path = tmp_path / name
    path.write_text(json.dumps(batch, ensure_ascii=False), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Existing contract coverage (now driven by the fake LLM)
# ---------------------------------------------------------------------------


def test_pipeline_produces_valid_output():
    output = run_pipeline(str(SAMPLE))
    assert isinstance(output, OutputBatch)
    assert output.status == "exito"
    assert output.resumen_comunidad.total_interacciones_procesadas == 10


def test_pipeline_routes_testimonios_to_linkedin():
    output = run_pipeline(str(SAMPLE))
    # The sample has 4 testimonios, so a LinkedIn post must be generated.
    assert output.activos_distribucion_generados.post_linkedin is not None


def test_pipeline_routes_questions_to_faq():
    output = run_pipeline(str(SAMPLE))
    # The sample has 3 technical questions, so a FAQ must be generated.
    assert output.activos_distribucion_generados.sugerencia_contenido_faq is not None


def test_pipeline_output_has_exact_contract_keys():
    output = run_pipeline(str(SAMPLE))
    claves = set(output.model_dump().keys())
    assert claves == {
        "status",
        "resumen_comunidad",
        "activos_distribucion_generados",
        "almacenamiento_oci",
    }


def test_pipeline_output_is_json_serializable():
    output = run_pipeline(str(SAMPLE))
    payload = output.model_dump_json(indent=2)
    assert '"status": "exito"' in payload


# ---------------------------------------------------------------------------
# Real wiring: decisions -> generators -> storage
# ---------------------------------------------------------------------------


def test_positive_testimonial_generates_linkedin_and_newsletter():
    output = run_pipeline(str(SAMPLE))
    assets = output.activos_distribucion_generados

    # Content comes from the real LinkedInGenerator (not a placeholder).
    assert assets.post_linkedin is not None
    assert assets.post_linkedin.titulo == "Titulo generado"
    assert assets.post_linkedin.copy == "Copy generado"

    # The newsletter is decoupled from LinkedIn: any actionable interaction
    # produces the highlight.
    assert assets.destaque_newsletter_semanal is not None
    assert assets.destaque_newsletter_semanal.titular == "Titular generado"


def test_technical_question_generates_faq_from_decision():
    output = run_pipeline(str(SAMPLE))
    faq = output.activos_distribucion_generados.sugerencia_contenido_faq

    assert faq is not None
    assert faq.tema == "Tema generado"
    # Code-owned metadata: origen from the first pregunta_tecnica channel.
    assert faq.origen == "#dudas-langgraph"
    assert faq.status == "derivado_a_mentoria"


def test_negative_testimonial_is_not_published(tmp_path):
    # The DECISION drives generation, not `tipo`: a testimonio whose analysis
    # says negativo must not produce a LinkedIn post nor a newsletter.
    source = _write_batch(
        tmp_path,
        [
            {
                "autor": "Raul",
                "canal": "#logros-y-empleos",
                "tipo": "testimonio",
                "texto": f"Me echaron del curso {NEGATIVE_MARKER}",
            }
        ],
    )
    output = run_pipeline(source)
    assets = output.activos_distribucion_generados

    assert assets.post_linkedin is None
    assert assets.destaque_newsletter_semanal is None
    assert assets.sugerencia_contenido_faq is None
    assert output.status == "exito"


def test_all_descartar_batch_yields_no_assets(tmp_path):
    source = _write_batch(
        tmp_path,
        [
            {
                "autor": "Luis",
                "canal": "#general",
                "tipo": "otro",
                "texto": "Buenos dias a todos.",
            },
            {
                "autor": "Jorge",
                "canal": "#feedback",
                "tipo": "feedback",
                "texto": "El taller estuvo bueno.",
            },
        ],
    )
    output = run_pipeline(source)
    assets = output.activos_distribucion_generados

    assert assets.post_linkedin is None
    assert assets.destaque_newsletter_semanal is None
    assert assets.sugerencia_contenido_faq is None

    # The storage record is still returned even with nothing to store.
    storage = output.almacenamiento_oci
    assert storage is not None
    assert storage.status == "pendiente"
    assert storage.ruta_objeto
    assert output.status == "exito"


def test_storage_without_oci_creds_writes_local_snapshot(tmp_path):
    output = run_pipeline(str(SAMPLE))
    storage = output.almacenamiento_oci

    assert storage.status == "pendiente"
    assert storage.ruta_objeto.startswith("storage/activos/")

    snapshot = tmp_path / storage.ruta_objeto
    assert snapshot.is_file()
    assert snapshot.name == f"paquete-distribucion-{date.today().isoformat()}.json"

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {
        "post_linkedin",
        "destaque_newsletter_semanal",
        "sugerencia_contenido_faq",
    }
    assert payload["post_linkedin"]["titulo"] == "Titulo generado"


def test_pipeline_with_rule_based_backend_offline_end_to_end(
    monkeypatch, tmp_path
):
    """End-to-end offline test with real RuleBasedClient backend."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    for var in (
        "OCI_USER_ID",
        "OCI_PRIVATE_KEY_PATH",
        "OCI_FINGERPRINT",
        "OCI_TENANCY_ID",
        "OCI_REGION",
    ):
        monkeypatch.delenv(var, raising=False)

    interacciones = [
        {
            "autor": "Test User",
            "canal": "#logros",
            "tipo": "testimonio",
            "texto": "Logré mi primer empleo como desarrollador!",
        },
        {
            "autor": "Dev",
            "canal": "#dudas",
            "tipo": "pregunta_tecnica",
            "texto": "¿Cómo hago para configurar esto?",
        },
        {
            "autor": "Otro",
            "canal": "#general",
            "tipo": "otro",
            "texto": "Solo pasando por acá, nada importante",
        },
    ]
    batch = {
        "origen_comunidad": "test",
        "periodo_referencia": "Semana_05",
        "interacciones": interacciones,
    }
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(batch, ensure_ascii=False), encoding="utf-8")

    output = run_pipeline(str(path))
    assert output.status == "exito"
    assert output.activos_distribucion_generados.post_linkedin is not None
    assert output.activos_distribucion_generados.destaque_newsletter_semanal is not None
    assert output.activos_distribucion_generados.sugerencia_contenido_faq is not None
    storage = output.almacenamiento_oci
    assert storage is not None
    assert storage.status == "pendiente"
    snapshot_path = tmp_path / storage.ruta_objeto
    assert snapshot_path.exists()


def test_storage_with_oci_creds_uploads_and_reports_guardado_con_exito(
    monkeypatch, tmp_path
):
    """R5: the OCI success path must report `guardado_con_exito` and the
    period-scoped object key from the contract example, using a simulated
    Object Storage client (no `oci` SDK required)."""
    monkeypatch.chdir(tmp_path)
    for var in (
        "OCI_USER_ID",
        "OCI_PRIVATE_KEY_PATH",
        "OCI_FINGERPRINT",
        "OCI_TENANCY_ID",
        "OCI_REGION",
    ):
        monkeypatch.setenv(var, "fake")

    calls = {}

    class _FakeObjectStorage:
        """Stands in for the real `oci.object_storage.ObjectStorageClient`."""

        def put_object(self, **kwargs):
            calls.update(kwargs)

    class _FakeOCI:
        """Stands in for `src.oci.client.OCIClient` (no SDK, no network)."""

        namespace = "axcyr94oehmi"

        def get_object_storage_client(self):
            return _FakeObjectStorage()

    monkeypatch.setattr("src.pipeline.OCIClient", _FakeOCI)

    output = run_pipeline(str(SAMPLE))
    storage = output.almacenamiento_oci

    assert storage.status == "guardado_con_exito"
    assert storage.bucket == "communitylab-activos-marketing"
    # Contract shape from the PDF: activos/<año>-semana-<n>/paquete-distribucion.json
    # (week "05" comes from SAMPLE's periodo_referencia; the ISO year tolerates
    # a year rollover).
    iso_year = date.today().isocalendar()[0]
    assert storage.ruta_objeto == f"activos/{iso_year}-semana-05/paquete-distribucion.json"

    # The simulated client really received the package.
    assert calls["bucket_name"] == "communitylab-activos-marketing"
    assert calls["object_name"] == storage.ruta_objeto
    assert calls["namespace_name"] == "axcyr94oehmi"
    body = json.loads(calls["put_object_body"].decode("utf-8"))
    assert body["post_linkedin"]["titulo"] == "Titulo generado"

    # The fallback snapshot must not be written on the happy path.
    assert not (tmp_path / "storage").exists()
