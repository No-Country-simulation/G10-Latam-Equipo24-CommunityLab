"""Tests for scripts/generar_muestra.py (sample regeneration CLI)."""
import importlib.util
import json
import os
from pathlib import Path

import src.interface.app as app_module

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "generar_muestra", REPO_ROOT / "scripts" / "generar_muestra.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canned_output():
    return {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 232,
            "feedback_negativo": 3,
        },
        "activos_distribucion_generados": {
            "candidatos_post_linkedin": [{"autor": "A"}, {"autor": "B"}],
        },
        "almacenamiento_oci": {},
    }


def test_main_writes_the_contract_output(monkeypatch, tmp_path):
    script = _load_script()
    canned = _canned_output()
    monkeypatch.setattr(
        app_module, "process_combined_sample", lambda *args, **kwargs: canned
    )
    output = tmp_path / "corrida-completa-gemma.json"
    monkeypatch.setattr(script, "OUTPUT", output)

    exit_code = script.main([])

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8")) == canned


def test_main_uses_configured_backend_by_default(monkeypatch, tmp_path):
    script = _load_script()
    seen_backend = {}

    def fake_process(*args, **kwargs):
        seen_backend["value"] = os.environ.get("COMMUNITYLAB_LLM_BACKEND")
        return _canned_output()

    monkeypatch.setattr(app_module, "process_combined_sample", fake_process)
    monkeypatch.setattr(script, "OUTPUT", tmp_path / "muestra.json")
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "ollama")

    script.main([])

    assert seen_backend["value"] == "ollama"


def test_main_offline_forces_rule_based_backend(monkeypatch, tmp_path):
    script = _load_script()
    seen_backend = {}

    def fake_process(*args, **kwargs):
        seen_backend["value"] = os.environ.get("COMMUNITYLAB_LLM_BACKEND")
        return _canned_output()

    monkeypatch.setattr(app_module, "process_combined_sample", fake_process)
    monkeypatch.setattr(script, "OUTPUT", tmp_path / "muestra.json")
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "ollama")

    script.main(["--offline"])

    assert seen_backend["value"] == "rule_based"


def test_main_fails_when_a_source_is_missing(monkeypatch, tmp_path):
    script = _load_script()
    monkeypatch.setattr(script, "SOURCES", [tmp_path / "no-existe.json"])

    exit_code = script.main([])

    assert exit_code == 1
