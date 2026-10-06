"""End-to-end pipeline test (HU-S3-005).

Runs the full pipeline on a 10-message sample and verifies the contract output.
Uses the rule_based backend by default (no API key), so it runs in CI.
"""
from pathlib import Path

from src.domain.models import OutputBatch
from src.pipeline import run_pipeline

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "pipeline_sample.json"


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
