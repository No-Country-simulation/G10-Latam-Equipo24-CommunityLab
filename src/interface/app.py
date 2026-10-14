import json
import tempfile
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from src.domain.models import InputBatch
from src.ingest.loader import load_batch
from src.pipeline import run_pipeline

# The LinkedIn post and newsletter editors are keyed per selected candidate
# (``linkedin_edit_<index>``). A widget with a key keeps its session value and
# ignores ``value=`` on later runs, so a single shared key leaked the previous
# testimonio's text into the editor after switching the selector. A key per
# candidate makes that stale state impossible by construction.
EDIT_WIDGET_KEY_PREFIXES = ("linkedin_edit", "news_edit")

EDIT_WIDGET_KEYS = (
    "linkedin_check",
    "news_check",
    "faq_edit",
    "faq_check",
)


def process_json_input(content):
    """Procesa un lote JSON y devuelve la salida del contrato."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "input.json"
        source.write_text(content, encoding="utf-8")
        result = run_pipeline(str(source)).model_dump()

    if result.get("status") != "exito":
        raise ValueError(f"El pipeline devolvió un estado inesperado: {result.get('status')!r}")
    return result


def process_combined_sample(sources, limits=None):
    """Combines several sample sources (JSON/CSV) into one batch and runs the pipeline.

    Parameters
    ----------
    sources : list
        Paths to the sample sources to merge, in order.
    limits : list | None
        Optional per-source caps aligned with `sources`: an int keeps the first
        N interactions, None keeps the whole source. When `limits` is absent,
        every source keeps its full content.

    Returns
    -------
    dict
        The contract dict produced by `process_json_input` on the merged batch.
    """
    batches = []
    for index, source in enumerate(sources):
        batch = load_batch(str(Path(source)))
        if limits is not None:
            limit = limits[index]
            if limit is not None:
                batch.interacciones = batch.interacciones[:limit]
        batches.append(batch)

    origen_comunidad = " + ".join(
        sorted({batch.origen_comunidad for batch in batches if batch.origen_comunidad})
    )
    periodos = sorted(
        {batch.periodo_referencia for batch in batches if batch.periodo_referencia}
    )
    periodo_referencia = periodos[0] if len(periodos) == 1 else "combinado"
    interacciones = [msg for batch in batches for msg in batch.interacciones]

    merged = InputBatch(
        origen_comunidad=origen_comunidad,
        periodo_referencia=periodo_referencia,
        interacciones=interacciones,
    )
    return process_json_input(merged.model_dump_json(indent=2))


def load_sample_results(path):
    """Carga los resultados de una corrida de ejemplo desde un archivo JSON.

    Parámetros
    ----------
    path : str | Path
        Ruta al JSON con la salida del contrato (estado "exito").

    Retorna
    -------
    dict | None
        El dict de resultados si el archivo existe, es JSON válido y su
        estado es "exito"; None en cualquier otro caso (archivo faltante,
        JSON malformado o estado inesperado).
    """
    sample_path = Path(path)
    if not sample_path.exists():
        return None
    try:
        data = json.loads(sample_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("status") != "exito":
        return None
    return data


def build_sentiment_distribution_df(distribucion_sentimiento):
    """Construye un DataFrame para el gráfico de distribución de sentimiento.

    Parámetros
    ----------
    distribucion_sentimiento : dict
        Conteos por sentimiento (claves: "positivo", "negativo", "neutral").

    Retorna
    -------
    pandas.DataFrame
        Columnas ["sentimiento", "conteo"] listas para graficar.
    """
    if not distribucion_sentimiento:
        return pd.DataFrame(columns=["sentimiento", "conteo"])

    data = []
    for sentiment, count in distribucion_sentimiento.items():
        try:
            data.append({"sentimiento": str(sentiment), "conteo": int(count)})
        except (ValueError, TypeError):
            continue

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["sentimiento", "conteo"])
    return df


def build_sentiment_pie_chart(df):
    """Builds an Altair pie (arc) chart for the sentiment distribution.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ["sentimiento", "conteo"] as produced by
        build_sentiment_distribution_df().

    Returns
    -------
    alt.Chart | None
        Arc chart with one slice per sentiment and a tooltip, or None when
        the DataFrame is empty or all counts are zero (nothing to render).
    """
    if df is None or df.empty:
        return None
    try:
        if df["conteo"].astype(int).sum() <= 0:
            return None
    except (KeyError, ValueError, TypeError):
        return None

    return (
        alt.Chart(df)
        .mark_arc()
        .encode(
            theta=alt.Theta(field="conteo", type="quantitative"),
            color=alt.Color(
                field="sentimiento",
                type="nominal",
                scale=alt.Scale(
                    domain=["positivo", "negativo", "neutral"],
                    range=["#4CAF50", "#F44336", "#9E9E9E"],
                ),
            ),
            tooltip=["sentimiento", "conteo"],
        )
        .properties(height=250)
    )


def build_top_topics_df(temas_principales_conteo):
    """Construye un DataFrame para el gráfico de temas principales (horizontal).

    Parámetros
    ----------
    temas_principales_conteo : list
        Lista de objetos con "tema" y "conteo".

    Retorna
    -------
    pandas.DataFrame
        Columnas ["tema", "conteo"] ordenadas desc por conteo.
    """
    if not temas_principales_conteo:
        return pd.DataFrame(columns=["tema", "conteo"])

    data = []
    for item in temas_principales_conteo:
        if isinstance(item, dict):
            tema = item.get("tema")
            conteo = item.get("conteo")
        else:
            tema = getattr(item, "tema", None)
            conteo = getattr(item, "conteo", None)
        if tema is None or conteo is None:
            continue
        try:
            data.append({"tema": str(tema), "conteo": int(conteo)})
        except (ValueError, TypeError):
            continue

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["tema", "conteo"])
    df = df.sort_values(by="conteo", ascending=False).reset_index(drop=True)
    return df


def build_linkedin_candidate_options(candidatos):
    """Builds the selectbox labels for the LinkedIn candidates.

    Each label is numbered so it stays unique even when two distinct
    candidates share the same author and the same start of the text. The app
    maps the selected label back to its candidate with ``list.index()``, which
    would otherwise always resolve to the FIRST match and load the wrong copy.
    """
    return [
        f"{index}. {candidato['autor']} - {candidato.get('texto_original', '')[:40]}"
        for index, candidato in enumerate(candidatos, start=1)
    ]


# Fields the selector swaps when a candidate carries its own full post.
_POST_VIEW_FIELDS = ("titulo", "copy", "canal_recomendado", "potencial_engagement")


def merge_post_view(linkedin, seleccionado):
    """Overlays the selected candidate's post over the published post.

    The published post is the base (it always carries every field); the
    selected candidate only overrides the fields it actually has, so old
    samples without the full post still render the published values.
    """
    view = dict(linkedin)
    if seleccionado:
        for key in _POST_VIEW_FIELDS:
            value = seleccionado.get(key)
            if value:
                view[key] = value
    return view


def merged_newsletter(newsletter, seleccionado):
    """Returns the selected candidate's newsletter, else the published one.

    The newsletter follows the selected publishable testimonio; when the
    candidate has no newsletter (old samples), the published highlight stays.
    """
    if seleccionado and seleccionado.get("newsletter_titular"):
        return {
            "seccion": seleccionado.get("newsletter_seccion", ""),
            "titular": seleccionado["newsletter_titular"],
            "resumen": seleccionado.get("newsletter_resumen", ""),
        }
    return newsletter


def build_assets_summary_df(resumen, assets):
    """Builds a DataFrame with the count of generated assets by type."""
    candidatos = (assets or {}).get("candidatos_post_linkedin") or []
    linkedin_count = len(candidatos)
    newsletter_count = 1 if (assets or {}).get("destaque_newsletter_semanal") else 0
    data = [
        {"activo": "Post LinkedIn", "conteo": linkedin_count},
        {"activo": "Newsletter", "conteo": newsletter_count},
        {"activo": "Dudas frecuentes (FAQ)", "conteo": int((resumen or {}).get("dudas_frecuentes", 0))},
        {"activo": "Derivados a humano", "conteo": int((resumen or {}).get("feedback_negativo", 0))},
    ]
    return pd.DataFrame(data)


def reset_batch_state(session_state):
    """Limpia resultados y ediciones anteriores antes de procesar un lote."""
    # The editors are keyed per candidate, so they are cleared by prefix: a new
    # batch must not inherit edits made for the previous one.
    for key in list(session_state.keys()):
        if key.startswith(EDIT_WIDGET_KEY_PREFIXES):
            session_state.pop(key, None)
    for key in EDIT_WIDGET_KEYS:
        session_state.pop(key, None)
    session_state["processing_done"] = False
    session_state["llm_results"] = None


def init_session_state():
    """Inicializa variables en session_state para mantener el flujo de la app."""
    if "processing_done" not in st.session_state:
        st.session_state.processing_done = False
    if "llm_results" not in st.session_state:
        st.session_state.llm_results = None


def main():
    st.set_page_config(
        page_title="CommunityLab - Panel de Curaduría",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()

    st.title("🚀 CommunityLab - Panel de Curaduría")
    st.markdown("---")

    st.header("1. Cargar Lote de Interacciones")
    st.write("Sube el archivo con los datos exportados de la comunidad (ej. Slack, Discord, Foro).")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader("Selecciona un archivo JSON", type=["json"])

    with col2:
        st.write("O ingresa JSON crudo:")
        raw_json_input = st.text_area("Pega el payload aquí...", height=100)

    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample" / "corrida-completa-gemma.json"
    sample_results = load_sample_results(sample_path)

    st.write("")
    if st.button("⚡ Cargar muestra de ejemplo", type="secondary", disabled=sample_results is None):
        reset_batch_state(st.session_state)
        st.session_state.llm_results = sample_results
        st.session_state.processing_done = True
        st.rerun()
    if sample_results is None:
        st.caption("La muestra de ejemplo no está disponible. Sube un archivo o pega el payload para continuar.")
    else:
        st.caption("Carga la corrida de ejemplo guardada (sin volver a ejecutar la IA).")

    combined_demo_sources = [
        Path(__file__).resolve().parents[2] / "data" / "sample" / "demo_fixed.json",
        Path(__file__).resolve().parents[2] / "data" / "sample" / "sintetico_120.csv",
        Path(__file__).resolve().parents[2] / "data" / "sample" / "mastodon_interacciones.json",
    ]
    combined_available = all(path.exists() for path in combined_demo_sources)

    combined_size = st.selectbox(
        "Tamaño del lote combinado",
        options=["Reducido (mitad por fuente)", "Completo (todas las interacciones)"],
        key="combined_size",
    )
    if combined_size == "Completo (todas las interacciones)":
        combined_limits = [None, None, None]
    else:
        combined_limits = [None, 60, 50]

    if st.button(
        "🧪 Procesar demo combinada (sintético + demo + mastodon)",
        type="secondary",
        key="combined_demo_button",
        disabled=not combined_available,
    ):
        reset_batch_state(st.session_state)
        try:
            with st.spinner("Procesando muestra demo combinada..."):
                st.session_state.llm_results = process_combined_sample(
                    combined_demo_sources, combined_limits
                )
                st.session_state.processing_done = True
        except Exception as exc:
            st.error(f"No se pudo procesar la demo combinada: {exc}")
        else:
            st.rerun()

    if combined_available:
        if combined_size == "Completo (todas las interacciones)":
            st.caption(
                "Procesa todas las interacciones de muestra: 12 demo, 120 sintéticas "
                "y 100 de Mastodon, 232 en total. La corrida completa es más lenta."
            )
        else:
            st.caption(
                "Procesa la muestra demo (Mariana Souza, Lucas) más la mitad de cada "
                "fuente sintética: 60 CSV y 50 de Mastodon, 122 interacciones en total."
            )
    else:
        st.caption("La demo combinada no está disponible. Faltan archivos de muestra.")

    data_ready = uploaded_file is not None or bool(raw_json_input.strip())

    if st.button("🧠 Procesar Interacciones con IA", type="primary", disabled=not data_ready, width="stretch"):
        reset_batch_state(st.session_state)
        try:
            content = (
                uploaded_file.getvalue().decode("utf-8")
                if uploaded_file is not None
                else raw_json_input
            )
            with st.spinner("Analizando comunidad y generando activos..."):
                st.session_state.llm_results = process_json_input(content)
                st.session_state.processing_done = True
        except Exception as exc:
            st.error(f"No se pudo procesar el lote: {exc}")
        else:
            st.rerun()

    if st.session_state.processing_done and st.session_state.llm_results:
        st.markdown("---")
        st.header("2. Activos Generados y Análisis")

        results = st.session_state.llm_results
        summary = results["resumen_comunidad"]
        assets = results["activos_distribucion_generados"]
        storage = results["almacenamiento_oci"]

        st.success(f"Estado del lote: {results['status']}")

        st.subheader("📊 Análisis Rápido")
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.metric(label="Total Interacciones", value=summary["total_interacciones_procesadas"])
        with kpi_col2:
            st.metric(label="Sentimiento", value=summary["sentimiento_predominante"])
        with kpi_col3:
            st.markdown("**Temas Principales:**")
            st.info(", ".join(summary["temas_principales"]))

        st.write("")
        st.subheader("🚨 Derivación a humano")
        deriv_col1, deriv_col2 = st.columns(2)
        feedback_negativo = summary.get("feedback_negativo", 0)
        analisis_degradados = summary.get("analisis_degradados", 0)
        with deriv_col1:
            st.metric(label="Derivados a humano", value=feedback_negativo)
        with deriv_col2:
            st.metric(label="Análisis degradados", value=analisis_degradados)

        if feedback_negativo > 0:
            st.warning(
                f"⚠️ {feedback_negativo} interacciones con feedback negativo "
                "se derivaron a revisión humana."
            )
        else:
            st.info(
                "No hubo interacciones con feedback negativo que requieran "
                "derivación a humano en este lote."
            )

        if analisis_degradados > 0:
            st.warning(
                f"⚠️ {analisis_degradados} análisis cayeron al valor "
                "predeterminado por un fallo del modelo (NEUTRO)."
            )
        else:
            st.caption("Sin análisis degradados.")

        st.write("")

        # Charts for Option A contract fields
        if "resumen_comunidad" in results:
            resumen = results["resumen_comunidad"]
            distribucion_df = build_sentiment_distribution_df(
                resumen.get("distribucion_sentimiento") or {}
            )
            temas_df = build_top_topics_df(
                resumen.get("temas_principales_conteo") or []
            )

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.subheader("Distribución de Sentimiento")
                chart = build_sentiment_pie_chart(distribucion_df)
                if chart is None:
                    st.info("No hay datos suficientes para mostrar la distribución de sentimiento.")
                else:
                    st.altair_chart(chart, use_container_width=True)

            with chart_col2:
                st.subheader("Temas Principales (Top)")
                if temas_df.empty:
                    st.info("No hay datos suficientes para mostrar temas principales.")
                else:
                    st.bar_chart(
                        temas_df,
                        x="tema",
                        y="conteo",
                        horizontal=True,
                    )

            st.subheader("📦 Activos generados por tipo")
            assets_df = build_assets_summary_df(
                resumen, results["activos_distribucion_generados"]
            )
            if assets_df.empty:
                st.info("No hay activos generados para mostrar.")
            else:
                st.bar_chart(
                    assets_df,
                    x="activo",
                    y="conteo",
                    horizontal=True,
                )
            st.caption(
                "Los candidatos de LinkedIn son los publicables; los derivados "
                "a humano salen del feedback negativo."
            )

        st.write("")

        st.subheader("📝 Edición de Activos de Marketing")
        # The selected candidate drives BOTH tabs: its full post (tab 1) and
        # its own newsletter highlight (tab 2).
        seleccionado = None
        selected_index = 0
        tab1, tab2, tab3 = st.tabs(["💼 Post LinkedIn", "📰 Newsletter", "❓ Sugerencia FAQ"])

        with tab1:
            linkedin = assets["post_linkedin"]
            if linkedin:
                candidatos = assets.get("candidatos_post_linkedin") or []
                if len(candidatos) > 1:
                    opciones = build_linkedin_candidate_options(candidatos)
                    selected_label = st.selectbox(
                        "Testimonio a publicar",
                        options=opciones,
                        key="linkedin_candidate",
                    )
                    selected_index = opciones.index(selected_label)
                    seleccionado = candidatos[selected_index]
                    st.caption(
                        "El post y la newsletter se generan para el testimonio "
                        "seleccionado. Se pueden editar antes de aprobar."
                    )

                post_view = merge_post_view(linkedin, seleccionado)
                st.write(f"**Título:** {post_view['titulo']}")
                st.write(f"**Canal recomendado:** {post_view['canal_recomendado']}")
                st.write(f"**Potencial de engagement:** {post_view['potencial_engagement']}")
                st.info("Revisa y ajusta el copy antes de aprobar.")
                linkedin_edited = st.text_area(
                    "Contenido del Post:",
                    value=post_view["copy"],
                    height=250,
                    key=f"linkedin_edit_{selected_index}",
                    width="stretch",
                )
                linkedin_approve = st.checkbox("✅ Aprobar Post de LinkedIn", value=True, key="linkedin_check")
            else:
                st.info("No se generó un post de LinkedIn para este lote.")
                linkedin_edited = ""
                linkedin_approve = False

        with tab2:
            newsletter = assets["destaque_newsletter_semanal"]
            newsletter = merged_newsletter(newsletter, seleccionado)
            if newsletter:
                st.write(f"**Sección:** {newsletter['seccion']}")
                st.write(f"**Titular:** {newsletter['titular']}")
                st.info("Resumen para incluir en el próximo correo semanal.")
                newsletter_edited = st.text_area("Contenido Newsletter:", value=newsletter["resumen"], height=200, key=f"news_edit_{selected_index}", width="stretch")
                newsletter_approve = st.checkbox("✅ Aprobar Newsletter", value=True, key="news_check")
            else:
                st.info("No se generó un destaque para la newsletter semanal.")
                newsletter_edited = ""
                newsletter_approve = False

        with tab3:
            faq = assets["sugerencia_contenido_faq"]
            if faq:
                st.write(f"**Origen:** {faq['origen']}")
                st.write(f"**Estado:** {faq['status']}")
                st.info("Pregunta frecuente detectada automáticamente para la base de conocimiento.")
                faq_edited = st.text_area("Entrada FAQ:", value=faq["tema"], height=200, key="faq_edit", width="stretch")
                faq_approve = st.checkbox("✅ Aprobar Sugerencia FAQ", value=True, key="faq_check")
            else:
                st.info("No se detectó una pregunta frecuente para este lote.")
                faq_edited = ""
                faq_approve = False

        payload_to_save = {
            "linkedin": linkedin_edited if linkedin_approve else None,
            "newsletter": newsletter_edited if newsletter_approve else None,
            "faq": faq_edited if faq_approve else None,
        }

        st.markdown("---")
        st.header("3. Confirmación y Guardado")
        st.caption(
            f"OCI: {storage['status']} | {storage['bucket']}/{storage['ruta_objeto']}"
        )
        st.write(
            "El pipeline guarda automáticamente el paquete generado en OCI cuando hay "
            "credenciales configuradas; de lo contrario, conserva un snapshot local. "
            "Las ediciones aprobadas se descargan como un JSON aparte."
        )

        if st.button("Aprobar activos seleccionados", type="primary", width="stretch"):
            if not any(value and value.strip() for value in payload_to_save.values()):
                st.warning("⚠️ Debes aprobar al menos un activo para poder guardarlo.")
            else:
                approved_count = sum(bool(value and value.strip()) for value in payload_to_save.values())
                st.info(
                    f"{approved_count} activos aprobados en esta sesión. "
                    f"El paquete generado tiene estado de almacenamiento {storage['status']}; "
                    "descarga el JSON para conservar estas ediciones."
                )

        approved_payload = {
            key: value for key, value in payload_to_save.items() if value and value.strip()
        }
        st.download_button(
            "Descargar activos aprobados (JSON)",
            data=json.dumps(approved_payload, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"activos-aprobados-{date.today()}.json",
            mime="application/json",
            disabled=not approved_payload,
            width="stretch",
        )


if __name__ == "__main__":
    main()
