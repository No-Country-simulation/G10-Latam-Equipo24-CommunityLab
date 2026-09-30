from pathlib import Path

import pytest
from src.domain.models import CommunitySummary, OCIStorage, OutputBatch
from src.interface import app


def test_process_json_input_calls_pipeline_and_returns_output(monkeypatch):
    output = OutputBatch(
        status="exito",
        resumen_comunidad=CommunitySummary(
            total_interacciones_procesadas=1,
            sentimiento_predominante="positivo",
            temas_principales=["aprendizaje"],
        ),
        activos_distribucion_generados={},
        almacenamiento_oci=OCIStorage(
            bucket="communitylab",
            ruta_objeto="batch.json",
            status="pending",
        ),
    )
    pipeline_calls = []

    def fake_run_pipeline(source):
        pipeline_calls.append((source, Path(source).read_text(encoding="utf-8")))
        return output

    monkeypatch.setattr(app, "run_pipeline", fake_run_pipeline)
    content = '{"interacciones": []}'

    result = app.process_json_input(content)

    assert result == output.model_dump()
    assert len(pipeline_calls) == 1
    source, written_content = pipeline_calls[0]
    assert source.endswith("input.json")
    assert written_content == content


def test_process_json_input_rejects_unexpected_pipeline_status(monkeypatch):
    output = OutputBatch(
        status="error",
        resumen_comunidad=CommunitySummary(
            total_interacciones_procesadas=0,
            sentimiento_predominante="neutral",
        ),
        activos_distribucion_generados={},
        almacenamiento_oci=OCIStorage(
            bucket="communitylab",
            ruta_objeto="batch.json",
            status="pending",
        ),
    )
    monkeypatch.setattr(app, "run_pipeline", lambda source: output)

    with pytest.raises(ValueError, match="estado inesperado"):
        app.process_json_input("{}")


def test_reset_batch_state_clears_results_and_previous_edits():
    session_state = {
        "linkedin_edit": "copy anterior",
        "linkedin_check": True,
        "news_edit": "resumen anterior",
        "news_check": True,
        "faq_edit": "tema anterior",
        "faq_check": True,
        "processing_done": True,
        "llm_results": {"status": "exito"},
    }

    app.reset_batch_state(session_state)

    assert session_state == {"processing_done": False, "llm_results": None}