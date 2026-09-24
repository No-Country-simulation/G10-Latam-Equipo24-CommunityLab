import time

import streamlit as st


def simulate_llm_processing(data):
    """
    Simula la llamada al backend (LangChain/n8n + LLM)
    Aquí irá la integración real de la API.
    """
    time.sleep(2)

    return {
        "status": "listo",
        "resumen_comunidad": {
            "total_interacciones": 142,
            "sentimiento_principal": "Positivo (85%)",
            "temas_principales": "Serverless, CI/CD, Observabilidad",
        },
        "activos_distribucion_generados": {
            "linkedin": "🚀 ¡Nuestra comunidad sigue creciendo e innovando!\n\nEsta semana, vimos un interés masivo en arquitecturas Serverless y pipelines de CI/CD. Es inspirador ver cómo se comparten conocimientos y se resuelven problemas complejos colaborativamente.\n\n👉 Destacamos el aporte de [Nombre de Usuario] sobre Observabilidad en entornos distribuidos. ¡Lectura recomendada!\n\n¿Tú qué herramientas estás utilizando para monitorizar tus servicios? Déjalo en los comentarios 👇\n\n#CommunityLab #Serverless #DevOps #Comunidad",
            "newsletter": "🔥 Lo Mejor de CommunityLab: Serverless en el Centro de la Escena\n\nTitular: La adopción Serverless domina la conversación comunitaria.\n\nResumen: Durante la última semana, analizamos más de 140 interacciones clave. El debate se centró fuertemente en los desafíos y beneficios de migrar a arquitecturas sin servidor. Además, compartimos casos de éxito sobre automatización de despliegues (CI/CD) que redujeron los tiempos de salida a producción en un 40%.\n\nLee el reporte completo aquí: [Enlace]",
            "faq": "**Pregunta detectada recurrentemente:**\n¿Cuáles son las mejores prácticas para manejar secretos y variables de entorno en despliegues automatizados (CI/CD)?\n\n**Borrador de Respuesta Sugerida:**\nPara manejar secretos de forma segura en CI/CD, recomendamos:\n1. Nunca almacenar secretos en texto plano en el repositorio (usar `.gitignore`).\n2. Utilizar un Gestor de Secretos (como OCI Vault, AWS Secrets Manager, etc.).\n3. Inyectar los secretos en tiempo de ejecución de la pipeline a través de variables de entorno de la plataforma de CI/CD, asegurando que estén enmascaradas en los logs.",
        },
        "almacenamiento_oci": {
            "bucket": "communitylab-activos-marketing",
            "estado": "pendiente",
        },
    }


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
        uploaded_file = st.file_uploader("Selecciona un archivo JSON o CSV", type=["json", "csv"])

    with col2:
        st.write("O ingresa JSON crudo:")
        raw_json_input = st.text_area("Pega el payload aquí...", height=100)

    data_ready = uploaded_file is not None or bool(raw_json_input.strip())

    if st.button("🧠 Procesar Interacciones con IA", type="primary", disabled=not data_ready, use_container_width=True):
        with st.spinner("Analizando comunidad y generando activos..."):
            st.session_state.llm_results = simulate_llm_processing(data="dummy_data")
            st.session_state.processing_done = True

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
            st.metric(label="Total Interacciones", value=summary["total_interacciones"])
        with kpi_col2:
            st.metric(label="Sentimiento", value=summary["sentimiento_principal"], delta="Bueno")
        with kpi_col3:
            st.markdown("**Temas Principales:**")
            st.info(summary["temas_principales"])

        st.write("")

        st.subheader("📝 Edición de Activos de Marketing")
        tab1, tab2, tab3 = st.tabs(["💼 Post LinkedIn", "📰 Newsletter", "❓ Sugerencia FAQ"])

        with tab1:
            st.info("Revisa y ajusta el copy antes de aprobar.")
            linkedin_edited = st.text_area("Contenido del Post:", value=assets["linkedin"], height=250, key="linkedin_edit")
            linkedin_approve = st.checkbox("✅ Aprobar Post de LinkedIn", value=True, key="linkedin_check")

        with tab2:
            st.info("Resumen para incluir en el próximo correo semanal.")
            newsletter_edited = st.text_area("Contenido Newsletter:", value=assets["newsletter"], height=200, key="news_edit")
            newsletter_approve = st.checkbox("✅ Aprobar Newsletter", value=True, key="news_check")

        with tab3:
            st.info("Pregunta frecuente detectada automáticamente para la base de conocimiento.")
            faq_edited = st.text_area("Entrada FAQ:", value=assets["faq"], height=200, key="faq_edit")
            faq_approve = st.checkbox("✅ Aprobar Sugerencia FAQ", value=True, key="faq_check")

        payload_to_save = {
            "linkedin": linkedin_edited if linkedin_approve else None,
            "newsletter": newsletter_edited if newsletter_approve else None,
            "faq": faq_edited if faq_approve else None,
        }

        st.markdown("---")
        st.header("3. Confirmación y Guardado")
        st.write("Los activos marcados como aprobados serán almacenados en el repositorio centralizado.")

        if st.button("☁️ Aprobar y Guardar en OCI Object Storage", type="primary", use_container_width=True):
            if not (linkedin_approve or newsletter_approve or faq_approve):
                st.warning("⚠️ Debes aprobar al menos un activo para poder guardarlo.")
            else:
                with st.spinner("Guardando en Oracle Cloud Infrastructure..."):
                    time.sleep(1.5)
                    bucket_name = results["almacenamiento_oci"]["bucket"]
                    approved_count = sum(value is not None for value in payload_to_save.values())
                    st.success(
                        f"🎉 ¡Se guardaron {approved_count} activos en el bucket: "
                        f"`{bucket_name}` de OCI!"
                    )
                    st.balloons()


if __name__ == "__main__":
    main()
