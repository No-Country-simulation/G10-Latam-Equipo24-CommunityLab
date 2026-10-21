import json
from pathlib import Path

import altair as alt
import pandas as pd
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
        "linkedin_estado_0": app.CURATION_STATUS_APPROVED,
        "news_edit": "resumen anterior",
        "news_estado_0": app.CURATION_STATUS_REJECTED,
        "faq_edit": "tema anterior",
        "faq_estado": app.CURATION_STATUS_APPROVED,
        "telegram_published_times": {"firma-anterior": "10:00"},
        "processing_done": True,
        "llm_results": {"status": "exito"},
    }

    app.reset_batch_state(session_state)

    # Las keys de estado se limpian: el widget vuelve a su default (Pendiente),
    # así un lote nuevo no hereda la decisión del lote anterior. Las firmas ya
    # publicadas también se olvidan para no bloquear al candidato del lote nuevo.
    assert session_state == {"processing_done": False, "llm_results": None}
    for key in ("linkedin_estado_0", "news_estado_0", "faq_estado", "telegram_published_times"):
        assert key not in session_state


def test_is_atendido_defaults_to_false():
    assert app.is_atendido({}, "m-1") is False


def test_set_atendido_stores_state_in_session():
    session_state = {}
    app.set_atendido(session_state, "m-1", True)
    assert app.is_atendido(session_state, "m-1") is True

    app.set_atendido(session_state, "m-1", False)
    assert app.is_atendido(session_state, "m-1") is False


def test_reset_batch_state_clears_derivados_state_and_widget_keys():
    session_state = {
        "derivados_atendidos": {"m-1": True},
        "derivado_atendido_m-1": True,
        "derivado_atendido_m-2": False,
        "processing_done": True,
        "llm_results": {"status": "exito"},
    }

    app.reset_batch_state(session_state)

    assert "derivados_atendidos" not in session_state
    assert "derivado_atendido_m-1" not in session_state
    assert "derivado_atendido_m-2" not in session_state


def test_build_derivados_entries_marks_attended_state():
    mensajes = [
        {
            "message_id": "m-1",
            "autor": "Nora",
            "canal": "#general",
            "texto_original": "No me gustó.",
            "razon": "Feedback negativo",
            "confianza": 0.85,
        },
        {
            "message_id": "m-2",
            "autor": "Luis",
            "canal": "#feedback",
            "texto_original": "Pésimo servicio.",
            "razon": "Feedback negativo",
            "confianza": 0.95,
        },
    ]
    session_state = {"derivados_atendidos": {"m-1": True}}

    entries = app.build_derivados_entries(mensajes, session_state)

    assert len(entries) == 2
    assert entries[0]["atendido"] is True
    assert entries[1]["atendido"] is False


def test_build_derivados_entries_uses_index_fallback_when_message_id_missing():
    mensajes = [
        {
            "message_id": "",
            "autor": "Nora",
            "canal": "#general",
            "texto_original": "No me gustó.",
            "razon": "Feedback negativo",
            "confianza": 0.85,
        },
    ]
    session_state = {"derivados_atendidos": {"idx-0": True}}

    entries = app.build_derivados_entries(mensajes, session_state)

    assert entries[0]["key"] == "idx-0"
    assert entries[0]["atendido"] is True


def test_derivados_tab_renders_without_exceptions():
    """La pestaña Derivados se renderiza sin excepciones con mensajes."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 2,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "t",
                "canal_recomendado": "linkedin",
                "potencial_engagement": "alto",
                "copy": "texto",
            },
            "destaque_newsletter_semanal": {
                "seccion": "x",
                "titular": "y",
                "resumen": "z",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
            "mensajes_derivados": [
                {
                    "message_id": "m-1",
                    "autor": "Nora",
                    "canal": "#general",
                    "texto_original": "No me gustó el taller.",
                    "razon": "Feedback negativo",
                    "confianza": 0.85,
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    tab_labels = [tab.label for tab in at.tabs]
    assert any("Derivados" in label for label in tab_labels)


def test_derivados_tab_toggle_updates_session_state():
    """Marcar un mensaje como atendido actualiza st.session_state."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 1,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": None,
            "destaque_newsletter_semanal": None,
            "sugerencia_contenido_faq": None,
            "mensajes_derivados": [
                {
                    "message_id": "m-1",
                    "autor": "Nora",
                    "canal": "#general",
                    "texto_original": "No me gustó el taller.",
                    "razon": "Feedback negativo",
                    "confianza": 0.85,
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    # Tabs render all children regardless of selection, so the toggle is
    # directly reachable without switching tabs.
    checkbox = next(cb for cb in at.checkbox if cb.label == "Atendido")
    assert checkbox.value is False

    checkbox.check().run()
    assert not at.exception
    assert at.session_state["derivados_atendidos"]["m-1"] is True
    assert at.session_state["derivado_atendido_m-1"] is True


def test_branding_assets_are_available():
    branding_dir = Path(app.__file__).resolve().parent / "assets" / "branding"
    assets = (
        app.BRAND_LOGO_PATH,
        app.BRAND_ICON_PATH,
        branding_dir / "communitylab-logo-monocromatico.png",
    )

    assert all(asset.is_file() for asset in assets)
    assert all(asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for asset in assets)


def test_build_sentiment_distribution_df_with_data():
    distribucion = {"positivo": 5, "negativo": 2, "neutral": 3}
    df = app.build_sentiment_distribution_df(distribucion)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["sentimiento", "conteo"]
    assert len(df) == 3


def test_build_sentiment_distribution_df_empty():
    df = app.build_sentiment_distribution_df({})

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["sentimiento", "conteo"]
    assert len(df) == 0


def test_build_top_topics_df_with_data():
    temas = [
        {"tema": "aprendizaje", "conteo": 10},
        {"tema": "empleos", "conteo": 5},
        {"tema": "proyectos", "conteo": 3},
    ]
    df = app.build_top_topics_df(temas)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["tema", "conteo"]
    assert len(df) == 3
    # Should be sorted desc by conteo
    assert df.iloc[0]["tema"] == "aprendizaje"


def test_build_top_topics_df_empty():
    df = app.build_top_topics_df([])

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["tema", "conteo"]
    assert len(df) == 0


def test_load_sample_results_reads_valid_output(tmp_path):
    sample = tmp_path / "corrida.json"
    sample.write_text(
        json.dumps(
            {
                "status": "exito",
                "resumen_comunidad": {
                    "total_interacciones_procesadas": 4,
                    "sentimiento_predominante": "positivo",
                    "temas_principales": ["backend"],
                    "distribucion_sentimiento": {"positivo": 2},
                    "temas_principales_conteo": [{"tema": "backend", "conteo": 1}],
                },
                "activos_distribucion_generados": {},
                "almacenamiento_oci": {
                    "bucket": "communitylab",
                    "ruta_objeto": "storage/x.json",
                    "status": "pendiente",
                },
            }
        ),
        encoding="utf-8",
    )

    result = app.load_sample_results(sample)

    assert result is not None
    assert result["status"] == "exito"
    assert result["resumen_comunidad"]["total_interacciones_procesadas"] == 4


def test_load_sample_results_returns_none_for_missing_file(tmp_path):
    result = app.load_sample_results(tmp_path / "no-existe.json")

    assert result is None


def test_load_sample_results_returns_none_for_invalid_status(tmp_path):
    sample = tmp_path / "corrida.json"
    sample.write_text(
        json.dumps({"status": "error", "resumen_comunidad": {}, "activos_distribucion_generados": {}}),
        encoding="utf-8",
    )

    result = app.load_sample_results(sample)

    assert result is None


def test_load_sample_results_returns_none_for_malformed_json(tmp_path):
    sample = tmp_path / "corrida.json"
    sample.write_text("{no es json", encoding="utf-8")

    result = app.load_sample_results(sample)

    assert result is None


def test_sample_button_renders_dashboard_without_exceptions():
    """El dashboard con resultados cargados no lanza errores de render.

    Es la regresión del fallo `bar_chart() got an unexpected keyword argument
    'orientation'`: el render real (AppTest) con resultados de Option A debe
    quedar sin excepciones.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 0,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "t",
                "canal_recomendado": "linkedin",
                "potencial_engagement": "alto",
                "copy": "texto",
            },
            "destaque_newsletter_semanal": {
                "seccion": "x",
                "titular": "y",
                "resumen": "z",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception


def test_render_with_derivadas_metrics():
    """El dashboard con métricas de derivación a humano no lanza errores.

    Ejercita la rama de advertencias: feedback_negativo > 0 y
    analisis_degradados > 0 renderizan ambos mensajes sin excepciones.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 6,
            "sentimiento_predominante": "negativo",
            "temas_principales": ["soporte"],
            "feedback_negativo": 2,
            "analisis_degradados": 1,
            "distribucion_sentimiento": {"positivo": 1, "negativo": 3, "neutral": 2},
            "temas_principales_conteo": [{"tema": "soporte", "conteo": 3}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "t",
                "canal_recomendado": "linkedin",
                "potencial_engagement": "alto",
                "copy": "texto",
            },
            "destaque_newsletter_semanal": {
                "seccion": "x",
                "titular": "y",
                "resumen": "z",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    metric_labels = [metric.label for metric in at.metric]
    assert "Feedback negativo" in metric_labels
    assert "Análisis degradados" in metric_labels

    warning_texts = [warning.value for warning in at.warning]
    assert any("feedback negativo" in text for text in warning_texts)
    assert any("valor predeterminado" in text for text in warning_texts)


def test_build_sentiment_pie_chart_with_data():
    df = app.build_sentiment_distribution_df({"positivo": 5, "negativo": 2, "neutral": 3})
    chart = app.build_sentiment_pie_chart(df)

    assert isinstance(chart, alt.Chart)


def test_build_sentiment_pie_chart_empty_df_returns_none():
    df = app.build_sentiment_distribution_df({})

    assert app.build_sentiment_pie_chart(df) is None


def test_build_sentiment_pie_chart_all_zero_counts_returns_none():
    df = app.build_sentiment_distribution_df(
        {"positivo": 0, "negativo": 0, "neutral": 0}
    )

    assert app.build_sentiment_pie_chart(df) is None


def test_build_sentiment_pie_chart_uses_brand_palette():
    """La torta usa la paleta de marca y ya no los colores Material legacy."""
    df = app.build_sentiment_distribution_df({"positivo": 5, "negativo": 2, "neutral": 3})
    chart = app.build_sentiment_pie_chart(df)

    color_range = chart.to_dict()["encoding"]["color"]["scale"]["range"]
    assert color_range == [app.BRAND_TEAL, app.BRAND_NEGATIVE, app.BRAND_NEUTRAL]
    for legacy in ("#4CAF50", "#F44336", "#9E9E9E"):
        assert legacy not in color_range


def _assert_descending_by_x(sort):
    """El sort del eje categórico debe ser descendente por el eje x.

    Altair serializa sort="-x" como string o como objeto de sort; aceptamos
    ambas formas para no acoplarnos a la serialización exacta.
    """
    if isinstance(sort, str):
        assert sort == "-x"
    else:
        assert sort.get("field") == "x"
        assert sort.get("order") == "descending"


def test_build_top_topics_chart_returns_none_for_empty_df():
    df = app.build_top_topics_df([])

    assert app.build_top_topics_chart(df) is None


def test_build_top_topics_chart_returns_none_for_none():
    assert app.build_top_topics_chart(None) is None


def test_build_top_topics_chart_pins_axis_at_zero_and_sorts_desc():
    df = app.build_top_topics_df(
        [
            {"tema": "aprendizaje", "conteo": 10},
            {"tema": "empleos", "conteo": 5},
        ]
    )

    chart = app.build_top_topics_chart(df)

    assert isinstance(chart, alt.Chart)
    spec = chart.to_dict()
    assert spec["encoding"]["x"]["scale"]["domainMin"] == 0
    _assert_descending_by_x(spec["encoding"]["y"]["sort"])
    assert spec["mark"]["color"] == app.BRAND_TEAL
    # Altair expands shorthand tooltips into field objects; assert on fields.
    tooltip_fields = {t["field"] for t in spec["encoding"]["tooltip"]}
    assert tooltip_fields == {"tema", "conteo"}


def test_build_assets_chart_returns_none_for_empty_df():
    df = pd.DataFrame(columns=["activo", "conteo"])

    assert app.build_assets_chart(df) is None


def test_build_assets_chart_returns_none_for_none():
    assert app.build_assets_chart(None) is None


def test_build_assets_chart_pins_axis_at_zero_and_sorts_desc():
    df = app.build_assets_summary_df(
        {"dudas_frecuentes": 3, "feedback_negativo": 2},
        {"candidatos_post_linkedin": [{"autor": "a"}, {"autor": "b"}]},
    )

    chart = app.build_assets_chart(df)

    assert isinstance(chart, alt.Chart)
    spec = chart.to_dict()
    assert spec["encoding"]["x"]["scale"]["domainMin"] == 0
    _assert_descending_by_x(spec["encoding"]["y"]["sort"])
    assert spec["mark"]["color"] == app.BRAND_TEAL
    # Altair expands shorthand tooltips into field objects; assert on fields.
    tooltip_fields = {t["field"] for t in spec["encoding"]["tooltip"]}
    assert tooltip_fields == {"activo", "conteo"}


def test_build_top_topics_chart_axis_uses_integer_ticks():
    """El eje de conteo debe marcar solo enteros, sin ticks decimales."""
    df = app.build_top_topics_df([{"tema": "aprendizaje", "conteo": 3}])

    spec = app.build_top_topics_chart(df).to_dict()

    assert spec["encoding"]["x"]["axis"]["tickMinStep"] == 1
    assert spec["encoding"]["x"]["axis"]["format"] == "d"


def test_build_assets_chart_axis_uses_integer_ticks():
    """El eje de conteo debe marcar solo enteros, sin ticks decimales."""
    df = app.build_assets_summary_df({}, {})

    spec = app.build_assets_chart(df).to_dict()

    assert spec["encoding"]["x"]["axis"]["tickMinStep"] == 1
    assert spec["encoding"]["x"]["axis"]["format"] == "d"


def test_top_topics_and_assets_charts_share_the_same_shape():
    """Los dos builders públicos deben producir la misma forma de gráfico."""
    topics = app.build_top_topics_chart(
        app.build_top_topics_df([{"tema": "aprendizaje", "conteo": 2}])
    )
    assets = app.build_assets_chart(
        pd.DataFrame([{"activo": "Post LinkedIn", "conteo": 2}])
    )

    topics_spec = topics.to_dict()
    assets_spec = assets.to_dict()

    assert topics_spec["mark"] == assets_spec["mark"]
    assert topics_spec["encoding"]["x"] == assets_spec["encoding"]["x"]
    assert topics_spec["encoding"]["y"]["sort"] == assets_spec["encoding"]["y"]["sort"]
    assert topics_spec["height"] == assets_spec["height"]
    topics_tooltip = {t["field"] for t in topics_spec["encoding"]["tooltip"]}
    assets_tooltip = {t["field"] for t in assets_spec["encoding"]["tooltip"]}
    assert topics_tooltip - {"tema"} == assets_tooltip - {"activo"}


def test_build_linkedin_candidate_options():
    candidatos = [
        {
            "autor": "Mariana Souza",
            "canal": "#logros-y-empleos",
            "texto_original": "Consegui mi primer empleo como desarrolladora junior",
            "relevancia": 0.95,
            "copy": "Copy de Mariana",
        },
        {
            "autor": "Lucas Albuquerque",
            "canal": "#logros-y-empleos",
            "texto_original": "Aprobe la certificacion de Oracle Cloud",
            "relevancia": 0.9,
            "copy": "Copy de Lucas",
        },
    ]

    labels = app.build_linkedin_candidate_options(candidatos)

    assert len(labels) == 2
    assert labels[0] == f"1. Mariana Souza - {candidatos[0]['texto_original'][:40]}"
    assert labels[1] == f"2. Lucas Albuquerque - {candidatos[1]['texto_original'][:40]}"


def test_build_linkedin_candidate_options_are_unique_when_labels_collide():
    """Dos candidatos distintos con el mismo autor y el mismo arranque de texto
    deben producir labels distintos; si no, el selectbox mapea al primero y
    devuelve el copy equivocado."""
    candidatos = [
        {
            "autor": "Jorge",
            "canal": "general",
            "texto_original": "Consegui mi primer empleo como desarrollador backend",
            "relevancia": 1.0,
            "copy": "Copy A",
        },
        {
            "autor": "Jorge",
            "canal": "general",
            "texto_original": "Consegui mi primer empleo como desarrollador backend",
            "relevancia": 1.0,
            "copy": "Copy B",
        },
    ]

    labels = app.build_linkedin_candidate_options(candidatos)

    assert len(labels) == 2
    assert len(set(labels)) == 2
    # Cada label debe mapear a su propio candidato (así se usa en la app:
    # candidatos[labels.index(selected_label)]).
    assert candidatos[labels.index(labels[0])]["copy"] == "Copy A"
    assert candidatos[labels.index(labels[1])]["copy"] == "Copy B"


def test_merge_post_view_prefers_the_selected_candidate():
    """El post publicado es la base; el candidato seleccionado lo pisa."""
    linkedin = {
        "titulo": "Titulo publicado",
        "canal_recomendado": "LinkedIn Oficial",
        "potencial_engagement": "Medio",
        "copy": "Copy publicado",
    }
    seleccionado = {
        "autor": "Lucas",
        "copy": "Copy de Lucas",
        "titulo": "Titulo de Lucas",
        "canal_recomendado": "LinkedIn de Lucas",
        "potencial_engagement": "Alto",
    }

    view = app.merge_post_view(linkedin, seleccionado)

    assert view["titulo"] == "Titulo de Lucas"
    assert view["canal_recomendado"] == "LinkedIn de Lucas"
    assert view["potencial_engagement"] == "Alto"
    assert view["copy"] == "Copy de Lucas"


def test_merge_post_view_falls_back_to_published_fields():
    """Un candidato viejo (sin post completo) no borra el post publicado."""
    linkedin = {
        "titulo": "Titulo publicado",
        "canal_recomendado": "LinkedIn Oficial",
        "potencial_engagement": "Medio",
        "copy": "Copy publicado",
    }
    seleccionado = {"autor": "Lucas", "copy": "Copy de Lucas"}

    view = app.merge_post_view(linkedin, seleccionado)

    assert view["titulo"] == "Titulo publicado"
    assert view["canal_recomendado"] == "LinkedIn Oficial"
    assert view["potencial_engagement"] == "Medio"
    assert view["copy"] == "Copy de Lucas"


def test_merge_post_view_without_selection_returns_published():
    linkedin = {"titulo": "t", "canal_recomendado": "c", "potencial_engagement": "p", "copy": "x"}
    assert app.merge_post_view(linkedin, None) == linkedin


def test_merged_newsletter_prefers_the_selected_candidate():
    """La newsletter sigue al testimonio seleccionado."""
    publicada = {"seccion": "x", "titular": "publicada", "resumen": "z"}
    seleccionado = {
        "newsletter_seccion": "Logro de la Semana",
        "newsletter_titular": "Titular de Lucas",
        "newsletter_resumen": "Resumen de Lucas",
    }

    newsletter = app.merged_newsletter(publicada, seleccionado)

    assert newsletter["seccion"] == "Logro de la Semana"
    assert newsletter["titular"] == "Titular de Lucas"
    assert newsletter["resumen"] == "Resumen de Lucas"


def test_merged_newsletter_falls_back_to_published():
    """Un candidato viejo (sin newsletter) conserva el destaque publicado."""
    publicada = {"seccion": "x", "titular": "publicada", "resumen": "z"}
    seleccionado = {"autor": "Lucas", "copy": "Copy de Lucas"}

    assert app.merged_newsletter(publicada, seleccionado) == publicada
    assert app.merged_newsletter(publicada, None) == publicada


def test_build_assets_summary_df_counts_assets_by_type():
    resumen = {"dudas_frecuentes": 3, "feedback_negativo": 2}
    assets = {
        "candidatos_post_linkedin": [{"autor": "a"}, {"autor": "b"}],
        "destaque_newsletter_semanal": {"seccion": "x"},
    }

    df = app.build_assets_summary_df(resumen, assets)

    assert len(df) == 4
    counts = dict(zip(df["activo"], df["conteo"]))
    assert counts["Post LinkedIn"] == 2
    assert counts["Newsletter"] == 1
    assert counts["Dudas frecuentes (FAQ)"] == 3
    assert counts["Feedback negativo"] == 2


def test_process_combined_sample_combines_sources_and_runs(tmp_path, monkeypatch):
    json_source = tmp_path / "demo_fixed.json"
    json_source.write_text(
        json.dumps(
            {
                "origen_comunidad": "Discord_Grupo_ONE_G10",
                "periodo_referencia": "Semana_04",
                "interacciones": [
                    {
                        "autor": "Mariana Souza",
                        "canal": "#logros-y-empleos",
                        "tipo": "testimonio",
                        "texto": "Logré el empleo",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    csv_source = tmp_path / "sintetico.csv"
    csv_source.write_text(
        "autor,canal,tipo,texto\n"
        "Jorge,general,logro,Migré mi app a OCI\n"
        "Ana,general,feedback,El servicio falló\n",
        encoding="utf-8",
    )

    captured = {}

    def fake_process_json_input(content):
        captured["content"] = content
        return {"status": "exito"}

    monkeypatch.setattr(app, "process_json_input", fake_process_json_input)

    result = app.process_combined_sample([json_source, csv_source])

    assert result == {"status": "exito"}
    merged = json.loads(captured["content"])
    autores = [msg["autor"] for msg in merged["interacciones"]]
    tipos = [msg["tipo"] for msg in merged["interacciones"]]
    assert len(merged["interacciones"]) == 3
    assert "Mariana Souza" in autores
    assert "Jorge" in autores
    assert "testimonio" in tipos
    assert "logro" in tipos


def test_process_combined_sample_limits_trim_each_source(tmp_path, monkeypatch):
    def write_json(path, origen, mensajes):
        path.write_text(
            json.dumps(
                {
                    "origen_comunidad": origen,
                    "periodo_referencia": "Semana_01",
                    "interacciones": mensajes,
                }
            ),
            encoding="utf-8",
        )

    def msg(autor, tipo):
        return {"autor": autor, "canal": "general", "tipo": tipo, "texto": "texto"}

    json_a = tmp_path / "a.json"
    write_json(json_a, "Comunidad_A", [msg("A1", "testimonio"), msg("A2", "feedback")])
    csv_b = tmp_path / "b.csv"
    csv_b.write_text(
        "autor,canal,tipo,texto\n"
        "B1,general,logro,x\n"
        "B2,general,logro,y\n"
        "B3,general,logro,z\n",
        encoding="utf-8",
    )
    json_c = tmp_path / "c.json"
    write_json(
        json_c,
        "Comunidad_C",
        [msg("C1", "pregunta_tecnica"), msg("C2", "discusion")],
    )

    captured = {}

    def fake_process_json_input(content):
        captured["content"] = content
        return {"status": "exito"}

    monkeypatch.setattr(app, "process_json_input", fake_process_json_input)

    result = app.process_combined_sample([json_a, csv_b, json_c], limits=[None, 1, None])

    assert result == {"status": "exito"}
    merged = json.loads(captured["content"])
    autores = [msg["autor"] for msg in merged["interacciones"]]
    tipos = {msg["tipo"] for msg in merged["interacciones"]}
    assert autores == ["A1", "A2", "B1", "C1", "C2"]
    assert len(merged["interacciones"]) == 5
    assert {"testimonio", "feedback", "logro", "pregunta_tecnica", "discusion"} <= tipos


def test_render_shows_combined_demo_button():
    """El botón y el selector de tamaño de demo combinada se renderizan."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    button_labels = [button.label for button in at.button]
    assert any("Procesar demo combinada" in label for label in button_labels)

    size_selectboxes = [
        selectbox
        for selectbox in at.selectbox
        if selectbox.label == "Tamaño del lote combinado"
    ]
    assert len(size_selectboxes) == 1
    assert size_selectboxes[0].value == "Reducido (mitad por fuente)"


def test_render_with_linkedin_candidates():
    """El selector de testimonio a publicar se renderiza con candidatos."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 0,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "t",
                "canal_recomendado": "linkedin",
                "potencial_engagement": "alto",
                "copy": "texto",
            },
            "destaque_newsletter_semanal": {
                "seccion": "x",
                "titular": "y",
                "resumen": "z",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
            "candidatos_post_linkedin": [
                {
                    "autor": "Mariana Souza",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Consegui mi primer empleo como desarrolladora junior",
                    "relevancia": 0.95,
                    "copy": "Copy de Mariana",
                },
                {
                    "autor": "Lucas Albuquerque",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Aprobe la certificacion de Oracle Cloud",
                    "relevancia": 0.9,
                    "copy": "Copy de Lucas",
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    selector_labels = [
        selectbox.label
        for selectbox in at.selectbox
        if selectbox.label == "Testimonio a publicar"
    ]
    assert len(selector_labels) == 1


def test_render_selector_swaps_post_and_newsletter():
    """Elegir un testimonio cambia el post completo Y la newsletter.

    Option A "grande": el selector ya no solo cambia el copy; el título, el
    canal, el engagement y el destaque de newsletter siguen al testimonio.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 0,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "Titulo publicado",
                "canal_recomendado": "LinkedIn Oficial",
                "potencial_engagement": "Medio",
                "copy": "Copy publicado",
            },
            "destaque_newsletter_semanal": {
                "seccion": "Logro de la Semana",
                "titular": "Titular publicado",
                "resumen": "Resumen publicado",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
            "candidatos_post_linkedin": [
                {
                    "autor": "Mariana Souza",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Consegui mi primer empleo como desarrolladora junior",
                    "relevancia": 0.95,
                    "copy": "Copy publicado",
                    "titulo": "Titulo publicado",
                    "canal_recomendado": "LinkedIn Oficial",
                    "potencial_engagement": "Medio",
                    "newsletter_seccion": "Logro de la Semana",
                    "newsletter_titular": "Titular publicado",
                    "newsletter_resumen": "Resumen publicado",
                },
                {
                    "autor": "Lucas Albuquerque",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Aprobe la certificacion de Oracle Cloud",
                    "relevancia": 0.9,
                    "copy": "Copy de Lucas",
                    "titulo": "Titulo de Lucas",
                    "canal_recomendado": "LinkedIn de Lucas",
                    "potencial_engagement": "Alto",
                    "newsletter_seccion": "Logro de la Semana",
                    "newsletter_titular": "Titular de Lucas",
                    "newsletter_resumen": "Resumen de Lucas",
                },
                {
                    "autor": "Sofia Ramos",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Termine mi primera app en produccion",
                    "relevancia": 0.85,
                    "copy": "Copy de Sofia",
                    "titulo": "Titulo de Sofia",
                    "canal_recomendado": "LinkedIn de Sofia",
                    "potencial_engagement": "Medio",
                    "newsletter_seccion": "Logro de la Semana",
                    "newsletter_titular": "Titular de Sofia",
                    "newsletter_resumen": "Resumen de Sofia",
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    # Default selection: the published post and its newsletter.
    markdown = "\n".join(node.value for node in at.markdown)
    assert "Titulo publicado" in markdown
    assert "Titular publicado" in markdown

    # Re-leer el selectbox en CADA paso: una referencia capturada antes de un
    # run() queda stale, y AppTest recolecta los widget states de esos elementos
    # viejos. Con keys por candidato eso pide una key que ya no existe
    # (KeyError: linkedin_edit_0) aunque la app este perfecta.
    selector = next(s for s in at.selectbox if s.label == "Testimonio a publicar")
    selector.select(selector.options[1]).run()
    assert not at.exception

    markdown = "\n".join(node.value for node in at.markdown)
    assert "Titulo de Lucas" in markdown
    assert "Titular de Lucas" in markdown
    assert "Titulo publicado" not in markdown
    assert "Titular publicado" not in markdown

    post_area = next(t for t in at.text_area if t.label == "Contenido del Post:")
    assert post_area.value == "Copy de Lucas"
    news_area = next(t for t in at.text_area if t.label == "Contenido Newsletter:")
    assert news_area.value == "Resumen de Lucas"

    # Segundo cambio consecutivo: el editor tiene que volver a sincronizarse.
    # Un st.text_area con key conserva el valor de session_state e ignora value=
    # en los re-runs, asi que sin re-sincronizar el primer cambio funcionaba y
    # los siguientes quedaban pegados al testimonio anterior.
    selector = next(s for s in at.selectbox if s.label == "Testimonio a publicar")
    selector.select(selector.options[2]).run()
    assert not at.exception

    markdown = "\n".join(node.value for node in at.markdown)
    assert "Titulo de Sofia" in markdown
    assert "Titular de Sofia" in markdown
    assert "Titulo de Lucas" not in markdown
    assert "Titular de Lucas" not in markdown

    post_area = next(t for t in at.text_area if t.label == "Contenido del Post:")
    assert post_area.value == "Copy de Sofia"
    news_area = next(t for t in at.text_area if t.label == "Contenido Newsletter:")
    assert news_area.value == "Resumen de Sofia"

    # Cada testimonio tiene su PROPIO editor: la key incluye el indice del
    # candidato. Con una key compartida ("linkedin_edit") el navegador seguia
    # mostrando el valor viejo de session_state porque la sesion le gana a
    # value= en los re-runs; AppTest no reproduce esa precedencia, asi que la
    # garantia que se fija aca es estructural: cada candidato guarda su edicion
    # bajo su propia key y ningun valor viejo puede filtrarse al siguiente.
    assert "linkedin_edit_2" in at.session_state
    assert at.session_state["linkedin_edit_2"] == "Copy de Sofia"
    assert "news_edit_2" in at.session_state
    assert at.session_state["news_edit_2"] == "Resumen de Sofia"
    assert "linkedin_edit" not in at.session_state
    assert "news_edit" not in at.session_state

    # Y volver al testimonio publicado tambien debe reflejarse.
    selector = next(s for s in at.selectbox if s.label == "Testimonio a publicar")
    selector.select(selector.options[0]).run()
    assert not at.exception
    markdown = "\n".join(node.value for node in at.markdown)
    assert "Titulo publicado" in markdown
    assert "Titulo de Sofia" not in markdown
    post_area = next(t for t in at.text_area if t.label == "Contenido del Post:")
    assert post_area.value == "Copy publicado"

    # Y una edicion manual de un testimonio no debe filtrarse al siguiente: es
    # el sintoma que reporto el usuario (cambiaba el titulo pero el texto grande
    # seguia pegado al testimonio anterior).
    edited_area = next(t for t in at.text_area if t.label == "Contenido del Post:")
    edited_area.set_value("EDICION MANUAL DEL USUARIO").run()
    assert at.session_state["linkedin_edit_0"] == "EDICION MANUAL DEL USUARIO"

    selector = next(s for s in at.selectbox if s.label == "Testimonio a publicar")
    selector.select(selector.options[1]).run()
    assert not at.exception
    post_area = next(t for t in at.text_area if t.label == "Contenido del Post:")
    assert post_area.value == "Copy de Lucas"
    assert at.session_state["linkedin_edit_1"] == "Copy de Lucas"


def test_render_with_assets_summary_chart():
    """La sección de activos por tipo se renderiza sin errores."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py"))
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 2,
            "analisis_degradados": 0,
            "dudas_frecuentes": 3,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "t",
                "canal_recomendado": "linkedin",
                "potencial_engagement": "alto",
                "copy": "texto",
            },
            "destaque_newsletter_semanal": {
                "seccion": "x",
                "titular": "y",
                "resumen": "z",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
            "candidatos_post_linkedin": [
                {
                    "autor": "Mariana Souza",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Consegui mi primer empleo como desarrolladora junior",
                    "relevancia": 0.95,
                    "copy": "Copy de Mariana",
                },
                {
                    "autor": "Lucas Albuquerque",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Aprobe la certificacion de Oracle Cloud",
                    "relevancia": 0.9,
                    "copy": "Copy de Lucas",
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }
    at.run()
    assert not at.exception

    subheaders = [subheader.value for subheader in at.subheader]
    assert any("Activos generados por tipo" in text for text in subheaders)


# ---------------------------------------------------------------------------
# Telegram publishing button
# ---------------------------------------------------------------------------

PUBLISH_BUTTON_LABEL = "📨 Publicar en Telegram"


def _llm_results_with_candidates():
    """Minimal successful llm_results with two LinkedIn candidates."""
    return {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 4,
            "sentimiento_predominante": "positivo",
            "temas_principales": ["backend"],
            "feedback_negativo": 0,
            "analisis_degradados": 0,
            "distribucion_sentimiento": {"positivo": 2, "neutral": 1},
            "temas_principales_conteo": [{"tema": "backend", "conteo": 2}],
        },
        "activos_distribucion_generados": {
            "post_linkedin": {
                "titulo": "Titulo publicado",
                "canal_recomendado": "LinkedIn Oficial",
                "potencial_engagement": "Medio",
                "copy": "Copy publicado",
            },
            "destaque_newsletter_semanal": {
                "seccion": "Logro de la Semana",
                "titular": "Titular publicado",
                "resumen": "Resumen publicado",
            },
            "sugerencia_contenido_faq": {
                "origen": "o",
                "status": "s",
                "tema": "q",
            },
            "candidatos_post_linkedin": [
                {
                    "autor": "Mariana Souza",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Consegui mi primer empleo como desarrolladora junior",
                    "relevancia": 0.95,
                    "copy": "Copy de Mariana",
                    "titulo": "Titulo de Mariana",
                    "canal_recomendado": "LinkedIn de Mariana",
                    "potencial_engagement": "Alto",
                },
                {
                    "autor": "Lucas Albuquerque",
                    "canal": "#logros-y-empleos",
                    "texto_original": "Aprobe la certificacion de Oracle Cloud",
                    "relevancia": 0.9,
                    "copy": "Copy de Lucas",
                    "titulo": "Titulo de Lucas",
                    "canal_recomendado": "LinkedIn de Lucas",
                    "potencial_engagement": "Medio",
                },
            ],
        },
        "almacenamiento_oci": {
            "bucket": "communitylab",
            "ruta_objeto": "storage/x.json",
            "status": "pendiente",
        },
    }


def _run_app_with_candidates(linkedin_estado=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(
        str(Path(app.__file__).resolve().parents[2] / "src" / "interface" / "app.py")
    )
    at.run()
    assert not at.exception

    at.session_state["processing_done"] = True
    at.session_state["llm_results"] = _llm_results_with_candidates()
    at.run()
    assert not at.exception

    # Pre-set the curation state when a test needs to skip the default
    # "Pendiente" (widget keys honor a session value over their default).
    if linkedin_estado is not None:
        at.session_state["linkedin_estado_0"] = linkedin_estado
        at.run()
        assert not at.exception
    return at


def _publish_button(at):
    return next(b for b in at.button if b.label == PUBLISH_BUTTON_LABEL)


def test_render_telegram_publish_button_in_linkedin_tab():
    """El botón de publicar en Telegram existe junto al post seleccionado."""
    at = _run_app_with_candidates()

    labels = [button.label for button in at.button]
    assert PUBLISH_BUTTON_LABEL in labels


def test_telegram_publish_without_config_warns_and_does_not_crash(monkeypatch):
    """Sin configuración, el click muestra la advertencia accionable."""
    from src.interface import telegram_publish

    # The dev machine could have these exported; force the unconfigured path
    # and prevent loading the real .env.
    monkeypatch.setattr(telegram_publish, "_ENV_LOADED", True)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()

    assert not at.exception
    warnings = [warning.value for warning in at.warning]
    assert any("TELEGRAM_BOT_TOKEN" in text for text in warnings)


def test_telegram_publish_success_renders_success(monkeypatch):
    """Con un publish_candidate fake, el click feliz muestra st.success."""
    from src.interface import telegram_publish

    llamadas = []

    def fake_publish(candidato, **kwargs):
        llamadas.append(candidato)
        return "texto publicado"

    monkeypatch.setattr(telegram_publish, "publish_candidate", fake_publish)

    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()

    assert not at.exception
    assert len(llamadas) == 1
    assert llamadas[0]["copy"] == "Copy de Mariana"
    successes = [success.value for success in at.success]
    assert any("Publicado en Telegram" in text for text in successes)


# ---------------------------------------------------------------------------
# Per-asset curation state (approve / pending / reject) and Telegram gate
# ---------------------------------------------------------------------------

CURATION_LABEL = "Estado de curaduría:"
APPROVE_BUTTON_LABEL = "Aprobar activos seleccionados"
SAMPLE_BUTTON_LABEL = "⚡ Cargar muestra de ejemplo"


def _curation_radio(at, key):
    return next(radio for radio in at.radio if radio.key == key)


def _run_app_with_curation(
    linkedin=app.CURATION_STATUS_PENDING,
    news=app.CURATION_STATUS_PENDING,
    faq=app.CURATION_STATUS_PENDING,
):
    at = _run_app_with_candidates()
    at.session_state["linkedin_estado_0"] = linkedin
    at.session_state["news_estado_0"] = news
    at.session_state["faq_estado"] = faq
    at.run()
    assert not at.exception
    return at


def _click_approve(at):
    next(b for b in at.button if b.label == APPROVE_BUTTON_LABEL).click().run()
    assert not at.exception


def test_curation_state_defaults_to_pending_for_every_asset():
    """Cada activo arranca en Pendiente y ofrece los tres estados."""
    at = _run_app_with_candidates()

    for key in ("linkedin_estado_0", "news_estado_0", "faq_estado"):
        radio = _curation_radio(at, key)
        assert radio.label == CURATION_LABEL
        assert radio.value == app.CURATION_STATUS_PENDING
        assert list(radio.options) == list(app.CURATION_STATUSES)


def test_approved_linkedin_is_included_in_approved_package():
    """Un activo Aprobado entra en el paquete aprobado/JSON descargable."""
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_APPROVED)

    _click_approve(at)

    infos = [info.value for info in at.info]
    assert any("1 activo aprobado" in text for text in infos)


def test_pending_and_rejected_assets_are_excluded_from_approved_package():
    """Pendiente y Rechazado NO entran en el paquete aprobado."""
    # Default: los tres activos en Pendiente.
    at = _run_app_with_candidates()
    _click_approve(at)
    warnings = [warning.value for warning in at.warning]
    assert any("Se debe aprobar al menos un activo" in text for text in warnings)

    # Rechazado: sigue afuera del paquete.
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_REJECTED)
    _click_approve(at)
    warnings = [warning.value for warning in at.warning]
    assert any("Se debe aprobar al menos un activo" in text for text in warnings)


def test_approved_asset_with_empty_text_is_excluded():
    """Aprobado pero con el editor vacío tampoco entra al paquete."""
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_APPROVED)

    editor = next(t for t in at.text_area if t.label == "Contenido del Post:")
    editor.set_value("").run()
    assert not at.exception

    _click_approve(at)

    warnings = [warning.value for warning in at.warning]
    assert any("Se debe aprobar al menos un activo" in text for text in warnings)


def test_approved_count_mentions_rejected_assets():
    """El resumen cuenta aprobados y menciona rechazados si los hay."""
    at = _run_app_with_curation(
        linkedin=app.CURATION_STATUS_APPROVED,
        news=app.CURATION_STATUS_REJECTED,
        faq=app.CURATION_STATUS_REJECTED,
    )

    _click_approve(at)

    infos = [info.value for info in at.info]
    assert any("1 activo aprobado" in text for text in infos)
    assert any("2 activos rechazados" in text for text in infos)


def test_publish_decision_blocks_when_not_approved():
    assert app.publish_decision(False, False) == app.PUBLISH_DECISION_NOT_APPROVED


def test_publish_decision_blocks_when_already_published():
    assert app.publish_decision(True, True) == app.PUBLISH_DECISION_ALREADY_PUBLISHED


def test_publish_decision_allows_approved_and_unsent():
    assert app.publish_decision(True, False) == app.PUBLISH_DECISION_APPROVED


def test_publish_decision_not_approved_takes_precedence():
    """Sin aprobación no se publica, aunque la firma ya se haya enviado."""
    assert app.publish_decision(False, True) == app.PUBLISH_DECISION_NOT_APPROVED


def test_publish_button_is_gated_by_linkedin_state():
    """El botón de publicar sólo se habilita con el LinkedIn Aprobado."""
    at = _run_app_with_candidates()

    assert _publish_button(at).proto.disabled is True
    captions = " \n".join(caption.value for caption in at.caption)
    assert "El post de LinkedIn debe estar aprobado" in captions

    at.session_state["linkedin_estado_0"] = app.CURATION_STATUS_REJECTED
    at.run()
    assert _publish_button(at).proto.disabled is True

    at.session_state["linkedin_estado_0"] = app.CURATION_STATUS_APPROVED
    at.run()
    assert _publish_button(at).proto.disabled is False


def test_approval_is_bound_to_the_selected_candidate(monkeypatch):
    """Aprobar un candidato no habilita publicar a OTRO: el estado va por candidato."""
    llamadas = _fake_publish_recorder(monkeypatch)
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()
    assert not at.exception
    assert len(llamadas) == 1

    # Cambiar de candidato no hereda la aprobación: el candidato 1 nunca fue
    # aprobado, así que el botón debe quedar deshabilitado.
    at.selectbox(key="linkedin_candidate").select_index(1).run()
    assert not at.exception
    assert _publish_button(at).disabled is True


def test_rejected_linkedin_shows_visible_warning_and_keeps_editor():
    """Un activo Rechazado avisa y deja el editor visible para reconsiderar."""
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_REJECTED)

    warnings = [warning.value for warning in at.warning]
    assert any("rechazado" in text.lower() for text in warnings)
    assert any(t.label == "Contenido del Post:" for t in at.text_area)


def test_destination_caption_shows_chat_before_button(monkeypatch):
    """Con configuración, el panel muestra el destino ANTES del botón."""
    from src.interface import telegram_publish

    monkeypatch.setattr(telegram_publish, "_ENV_LOADED", True)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-falso-que-nunca-debe-aparecer")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999888777")

    # El gate combinado exige Aprobado: sin eso el botón no se habilita.
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    assert not at.exception
    captions = [caption.value for caption in at.caption]
    assert any("Se va a publicar en el chat 999888777" in text for text in captions)
    assert all("token-falso-que-nunca-debe-aparecer" not in text for text in captions)
    assert _publish_button(at).disabled is False


def test_destination_warning_before_click_when_unconfigured(monkeypatch):
    """Sin configuración, la advertencia nombra las variables SIN clickear."""
    from src.interface import telegram_publish

    monkeypatch.setattr(telegram_publish, "_ENV_LOADED", True)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    at = _run_app_with_candidates()

    assert not at.exception
    warnings = [warning.value for warning in at.warning]
    assert any(
        "TELEGRAM_BOT_TOKEN" in text and "TELEGRAM_CHAT_ID" in text for text in warnings
    )


def test_metadata_caption_keeps_canal_autor_relevancia_for_curator():
    """La metadata de curaduría sigue visible en el panel, junto al publicar."""
    at = _run_app_with_candidates()

    assert not at.exception
    captions = [caption.value for caption in at.caption]
    assert any("Canal sugerido: LinkedIn de Mariana" in text for text in captions)
    assert any("Autor: Mariana Souza" in text for text in captions)
    assert any("Relevancia: 95%" in text for text in captions)


def test_preview_shows_only_the_post_body():
    """La vista previa (la misma que se envía) no muestra metadata."""
    at = _run_app_with_candidates()

    assert not at.exception
    previews = [text.value for text in at.text if "Copy de Mariana" in text.value]
    assert previews, "no se encontró la vista previa del mensaje"
    for preview in previews:
        assert "Canal sugerido" not in preview
        assert "Autor:" not in preview
        assert "Relevancia" not in preview
    assert "Titulo de Mariana\n\nCopy de Mariana" in previews


def _fake_publish_recorder(monkeypatch):
    from src.interface import telegram_publish

    llamadas = []

    def fake_publish(candidato, **kwargs):
        llamadas.append(candidato)
        return "texto publicado"

    monkeypatch.setattr(telegram_publish, "publish_candidate", fake_publish)
    return llamadas


def test_rejected_publish_flow_never_invokes_publish_candidate(monkeypatch):
    """Con Rechazado, intentar publicar NO llama a publish_candidate."""
    from streamlit.testing.v1.errors import AppTestError

    from src.interface import telegram_publish

    llamadas = []

    def fake_publish(candidato, **kwargs):
        llamadas.append(candidato)
        return "texto publicado"

    monkeypatch.setattr(telegram_publish, "publish_candidate", fake_publish)

    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_REJECTED)

    # El gate deshabilita el botón: AppTest se niega a interactuar con un
    # widget deshabilitado, igual que un usuario en el navegador. El flujo de
    # publicación es inalcanzable y el mock nunca se invoca.
    with pytest.raises(AppTestError):
        _publish_button(at).click().run()

    assert llamadas == []


def test_new_batch_does_not_inherit_previous_curation_state():
    """Cargar un lote nuevo devuelve los estados a Pendiente."""
    at = _run_app_with_candidates()
    _curation_radio(at, "linkedin_estado_0").set_value(app.CURATION_STATUS_APPROVED).run()
    assert not at.exception
    assert _curation_radio(at, "linkedin_estado_0").value == app.CURATION_STATUS_APPROVED

    next(button for button in at.button if button.label == SAMPLE_BUTTON_LABEL).click().run()
    assert not at.exception

    assert _curation_radio(at, "linkedin_estado_0").value == app.CURATION_STATUS_PENDING


def test_publish_button_disables_and_blocks_second_send(monkeypatch):
    """Tras un envío exitoso el botón queda deshabilitado para esa firma."""
    from streamlit.testing.v1 import AppTestError

    llamadas = _fake_publish_recorder(monkeypatch)
    # El gate combinado exige Aprobado para llegar a enviar.
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()
    assert not at.exception
    assert len(llamadas) == 1

    # Re-run: mismo candidato, mismo copy -> deshabilitado + hora del envío.
    at.run()
    assert not at.exception
    button = _publish_button(at)
    assert button.disabled is True
    assert any("✅ Publicado a las" in caption.value for caption in at.caption)
    assert len(llamadas) == 1

    # A browser user cannot click a disabled widget: AppTest rejects it.
    with pytest.raises(AppTestError):
        button.click()
    assert len(llamadas) == 1


def test_stale_click_does_not_resend_the_same_signature(monkeypatch):
    """Guardia defensiva: un click viejo sobre la misma firma no reenvía."""
    from streamlit.testing.v1.element_tree import Widget

    llamadas = _fake_publish_recorder(monkeypatch)
    # El gate combinado exige Aprobado para llegar a enviar.
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()
    assert len(llamadas) == 1
    at.run()
    assert _publish_button(at).disabled is True

    # Simulate a queued click reaching the disabled widget: bypass AppTest's
    # interaction guard so the handler itself must defend against a resend.
    monkeypatch.setattr(Widget, "_assert_can_interact", lambda self: None)
    _publish_button(at).click().run()

    assert not at.exception
    assert len(llamadas) == 1


def test_stale_click_without_approval_never_publishes(monkeypatch):
    """Guardia defensiva: un click viejo sin Aprobado no publica."""
    from streamlit.testing.v1.element_tree import Widget

    llamadas = _fake_publish_recorder(monkeypatch)
    # NO aprobado: el gate deshabilita el botón.
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_PENDING)
    assert _publish_button(at).disabled is True

    # Simular un click encolado que llega al widget deshabilitado: el handler
    # debe revalidar por su cuenta y no publicar.
    monkeypatch.setattr(Widget, "_assert_can_interact", lambda self: None)
    _publish_button(at).click().run()

    assert not at.exception
    assert llamadas == []


def test_editing_copy_reenables_publish_button(monkeypatch):
    """Editar el copy cambia la firma y el botón vuelve a habilitarse."""
    llamadas = _fake_publish_recorder(monkeypatch)
    # El gate combinado exige Aprobado para llegar a enviar.
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()
    assert len(llamadas) == 1
    at.run()
    assert _publish_button(at).disabled is True

    at.text_area(key="linkedin_edit_0").set_value("Copy editado despues de publicar").run()
    assert not at.exception
    button = _publish_button(at)
    assert button.disabled is False

    button.click().run()
    assert not at.exception
    assert len(llamadas) == 2
    assert llamadas[1]["copy"] == "Copy editado despues de publicar"


def test_switching_to_non_approved_candidate_keeps_publish_button_disabled(monkeypatch):
    """Aprobar un candidato no aprueba a otro: el estado va por candidato."""
    llamadas = _fake_publish_recorder(monkeypatch)
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)

    _publish_button(at).click().run()
    assert not at.exception
    assert len(llamadas) == 1

    # Cambiar de candidato NO hereda la aprobación: el nuevo candidato sigue
    # en Pendiente y el botón queda deshabilitado.
    at.selectbox(key="linkedin_candidate").select_index(1).run()
    assert not at.exception
    assert _publish_button(at).disabled is True

    # Recién al aprobar ESE candidato el botón se vuelve a habilitar.
    _curation_radio(at, "linkedin_estado_1").set_value(app.CURATION_STATUS_APPROVED).run()
    assert not at.exception
    button = _publish_button(at)
    assert button.disabled is False

    button.click().run()
    assert not at.exception
    assert len(llamadas) == 2
    assert llamadas[1]["titulo"] == "Titulo de Lucas"


def test_publish_button_requires_approval_and_unsent_signature(monkeypatch):
    """Gate combinado: sin Aprobado y ya publicado, ambos deshabilitan."""
    llamadas = _fake_publish_recorder(monkeypatch)

    # Nunca publicado, pero NO aprobado: el gate de curaduría lo deshabilita.
    at = _run_app_with_curation(linkedin=app.CURATION_STATUS_PENDING)
    assert _publish_button(at).disabled is True
    assert llamadas == []

    # Aprobado y recién enviado: el gate de firma lo deja deshabilitado.
    at = _run_app_with_candidates(linkedin_estado=app.CURATION_STATUS_APPROVED)
    assert _publish_button(at).disabled is False

    _publish_button(at).click().run()
    assert not at.exception
    assert len(llamadas) == 1

    at.run()
    assert not at.exception
    assert _publish_button(at).disabled is True
