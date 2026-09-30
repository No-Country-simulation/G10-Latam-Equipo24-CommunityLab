from pathlib import Path

from src.domain.models import CommunitySummary, OCIStorage, OutputBatch
from src.interface import app


def test_process_json_input_calls_pipeline_and_returns_output(monkeypatch):
    output = OutputBatch(
        status="success",
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