import tempfile
from pathlib import Path

import streamlit as st
from src.pipeline import run_pipeline


def process_json_input(content):
    """Passes JSON text to the file-based pipeline and returns its output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "input.json"
        source.write_text(content, encoding="utf-8")
        return run_pipeline(str(source)).model_dump()


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

    data_ready = uploaded_file is not None or bool(raw_json_input.strip())

    if st.button("🧠 Procesar Interacciones con IA", type="primary", disabled=not data_ready, use_container_width=True):
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

        st.subheader("📝 Edición de Activos de Marketing")
        tab1, tab2, tab3 = st.tabs(["💼 Post LinkedIn", "📰 Newsletter", "❓ Sugerencia FAQ"])

        with tab1:
            linkedin = assets["post_linkedin"]
            if linkedin:
                st.info("Revisa y ajusta el copy antes de aprobar.")
                linkedin_edited = st.text_area("Contenido del Post:", value=linkedin["copy"], height=250, key="linkedin_edit")
                linkedin_approve = st.checkbox("✅ Aprobar Post de LinkedIn", value=True, key="linkedin_check")
            else:
                st.info("No se generó un post de LinkedIn para este lote.")
                linkedin_edited = ""
                linkedin_approve = False

        with tab2:
            newsletter = assets["destaque_newsletter_semanal"]
            if newsletter:
                st.info("Resumen para incluir en el próximo correo semanal.")
                newsletter_edited = st.text_area("Contenido Newsletter:", value=newsletter["resumen"], height=200, key="news_edit")
                newsletter_approve = st.checkbox("✅ Aprobar Newsletter", value=True, key="news_check")
            else:
                st.info("No se generó un destaque para la newsletter semanal.")
                newsletter_edited = ""
                newsletter_approve = False

        with tab3:
            faq = assets["sugerencia_contenido_faq"]
            if faq:
                st.info("Pregunta frecuente detectada automáticamente para la base de conocimiento.")
                faq_edited = st.text_area("Entrada FAQ:", value=faq["tema"], height=200, key="faq_edit")
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
        st.write("Los activos aprobados quedan seleccionados en esta sesión. El guardado en OCI aún no está integrado.")

        if st.button("Aprobar activos seleccionados", type="primary", use_container_width=True):
            if not (linkedin_approve or newsletter_approve or faq_approve):
                st.warning("⚠️ Debes aprobar al menos un activo para poder guardarlo.")
            else:
                approved_count = sum(value is not None for value in payload_to_save.values())
                st.warning(
                    f"{approved_count} activos aprobados en esta sesión. "
                    "El pipeline todavía no los ha guardado en OCI."
                )


if __name__ == "__main__":
    main()
