import base64
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ``streamlit run src/interface/app.py`` puts only the folder holding this file
# on ``sys.path``, never the repository root. Locally that goes unnoticed
# because the process usually starts from the repository root, but Streamlit
# Community Cloud runs the app from a freshly built environment where every
# ``from src...`` import below fails with
# ``ModuleNotFoundError: No module named 'src'``. Inserting the root here is
# idempotent and makes the app run under either entry point.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Imported before the ``src.*`` modules on purpose: it maps
# ``.streamlit/secrets.toml`` into the environment so the cloud deployment
# sees the same ``os.getenv`` values that a local ``.env`` provides. It must
# run before ``src.pipeline`` / ``src.oci`` are imported below.
import src.interface.cloud_secrets  # noqa: E402, F401  (side-effect import)
from src.domain.models import InputBatch  # noqa: E402
from src.ingest.loader import load_batch  # noqa: E402
from src.interface import telegram_publish  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402

# The LinkedIn post and newsletter editors are keyed per selected candidate
# (``linkedin_edit_<index>``) and so are their curation-state radios
# (``linkedin_estado_<index>``, ``news_estado_<index>``). A widget with a key
# keeps its session value and ignores ``value=`` on later runs, so a single
# shared key leaked the previous testimonio's text into the editor — and its
# approval state — after switching the selector. A key per candidate makes that
# stale state impossible by construction.
EDIT_WIDGET_KEY_PREFIXES = ("linkedin_edit", "news_edit", "linkedin_estado", "news_estado")

EDIT_WIDGET_KEYS = (
    "faq_edit",
    "faq_estado",
)

# Prefix for the per-derived-message toggle keys in session_state. These are
# cleared on every new batch so attended states do not leak across runs.
DERIVED_WIDGET_KEY_PREFIX = "derivado_atendido_"

BRAND_LOGO_PATH = Path(__file__).resolve().parent.joinpath(
    "assets", "branding", "communitylab-logo-principal.png"
)
BRAND_ICON_PATH = Path(__file__).resolve().parent.joinpath(
    "assets", "branding", "communitylab-isotipo-fondo-azul.png"
)

# Brand palette: aligns with .streamlit/config.toml and the hero CSS in
# apply_dashboard_styles() so charts share the dashboard accent colours.
BRAND_NAVY = "#0B2D4A"
BRAND_TEAL = "#00C2AB"
BRAND_VIOLET = "#7C3AED"
# Harmonised chart tones that complement the brand palette.
BRAND_NEUTRAL = "#8CA0B3"  # grey-blue
BRAND_NEGATIVE = "#E2574C"  # tempered red

# Estado de curaduría por activo. Los nombres de constante van en inglés y los
# valores en español porque son copy de UI (radio buttons en el panel).
CURATION_STATUS_PENDING = "Pendiente"
CURATION_STATUS_APPROVED = "Aprobado"
CURATION_STATUS_REJECTED = "Rechazado"
CURATION_STATUSES = (
    CURATION_STATUS_PENDING,
    CURATION_STATUS_APPROVED,
    CURATION_STATUS_REJECTED,
)


# Decisión del handler de publicación, como función pura para poder cubrir sus
# tres resultados sin depender del runtime de Streamlit: un botón deshabilitado
# descarta el click del lado del servidor, así que las ramas defensivas del
# handler no se alcanzan desde la UI.
PUBLISH_DECISION_NOT_APPROVED = "not_approved"
PUBLISH_DECISION_ALREADY_PUBLISHED = "already_published"
PUBLISH_DECISION_APPROVED = "publish"


def publish_decision(linkedin_aprobado, ya_publicado):
    """Devuelve qué hacer con el click del botón de publicar en Telegram."""
    if not linkedin_aprobado:
        return PUBLISH_DECISION_NOT_APPROVED
    if ya_publicado:
        return PUBLISH_DECISION_ALREADY_PUBLISHED
    return PUBLISH_DECISION_APPROVED


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
                    range=[BRAND_TEAL, BRAND_NEGATIVE, BRAND_NEUTRAL],
                ),
            ),
            tooltip=["sentimiento", "conteo"],
        )
        .properties(height=250)
    )


def _build_count_chart(df, category_col, category_title):
    """Builds a horizontal Altair bar chart of counts by category.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns [category_col, "conteo"].
    category_col : str
        Name of the nominal column plotted on the y axis.
    category_title : str
        Title shown on the y axis.

    Returns
    -------
    alt.Chart | None
        Horizontal bar chart sorted descending by count, with the numeric
        axis pinned at zero and integer ticks, or None when the DataFrame
        is empty.
    """
    if df is None or df.empty:
        return None
    return (
        alt.Chart(df)
        .mark_bar(color=BRAND_TEAL)
        .encode(
            x=alt.X("conteo:Q", scale=alt.Scale(domainMin=0), title="Conteo", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y(f"{category_col}:N", sort="-x", title=category_title),
            tooltip=[category_col, "conteo"],
        )
        .properties(height=max(180, 26 * len(df)))
    )


def build_top_topics_chart(df):
    """Builds a horizontal Altair bar chart for the top community topics.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ["tema", "conteo"] as produced by
        build_top_topics_df().

    Returns
    -------
    alt.Chart | None
        Horizontal bar chart sorted descending by count, with the numeric
        axis pinned at zero, or None when the DataFrame is empty.
    """
    return _build_count_chart(df, "tema", "Tema")


def build_assets_chart(df):
    """Builds a horizontal Altair bar chart for the generated assets by type.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns ["activo", "conteo"] as produced by
        build_assets_summary_df().

    Returns
    -------
    alt.Chart | None
        Horizontal bar chart sorted descending by count, with the numeric
        axis pinned at zero, or None when the DataFrame is empty.
    """
    return _build_count_chart(df, "activo", "Activo")


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


def _curation_metadata_line(candidato):
    """Curator-only metadata (canal/autor/relevancia) shown near the publish area.

    This line is for the human reviewing the post; it is NEVER part of the
    published message, which is built exclusively by
    ``telegram_publish.format_candidate_message``.
    """
    partes = []
    canal = str(candidato.get("canal_recomendado") or "").strip()
    if canal:
        partes.append(f"Canal sugerido: {canal}")
    autor = str(candidato.get("autor") or "").strip()
    if autor:
        partes.append(f"Autor: {autor}")
    relevancia = candidato.get("relevancia")
    if relevancia not in (None, ""):
        try:
            partes.append(f"Relevancia: {float(relevancia):.0%}")
        except (TypeError, ValueError):
            partes.append(f"Relevancia: {relevancia}")
    return " · ".join(partes)


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
        {"activo": "Feedback negativo", "conteo": int((resumen or {}).get("feedback_negativo", 0))},
    ]
    return pd.DataFrame(data)


def is_atendido(session_state, message_id):
    """Returns whether a derived message is marked as attended in session_state.

    Falls back to ``False`` when the dict or key is missing, so a fresh render
    shows every derivation as pending.
    """
    return bool((session_state or {}).get("derivados_atendidos", {}).get(message_id))


def set_atendido(session_state, message_id, value):
    """Marks a derived message as attended (or not) in session_state."""
    session_state.setdefault("derivados_atendidos", {})[message_id] = bool(value)


def build_derivados_entries(mensajes, session_state):
    """Builds the list rendered by the "Derivados" tab.

    Each entry carries the original message fields plus an ``atendido`` flag
    and a stable ``key`` for the toggle widget. When a message lacks an id,
    the key falls back to ``idx-<position>`` so the UI can still track state.
    """
    attended = (session_state or {}).get("derivados_atendidos", {})
    entries = []
    for position, mensaje in enumerate(mensajes):
        message_id = str(mensaje.get("message_id") or "").strip()
        key = message_id if message_id else f"idx-{position}"
        entries.append(
            {
                "key": key,
                "message_id": message_id,
                "autor": mensaje.get("autor", ""),
                "canal": mensaje.get("canal", ""),
                "texto_original": mensaje.get("texto_original", ""),
                "razon": mensaje.get("razon", ""),
                "confianza": mensaje.get("confianza", 0.0),
                "atendido": bool(attended.get(key)),
            }
        )
    return entries


def reset_batch_state(session_state):
    """Limpia resultados y ediciones anteriores antes de procesar un lote."""
    # The editors and their state radios are keyed per candidate, so they are
    # cleared by prefix: a new batch must not inherit edits or decisions made
    # for the previous one.
    for key in list(session_state.keys()):
        if key.startswith(EDIT_WIDGET_KEY_PREFIXES):
            session_state.pop(key, None)
    for key in EDIT_WIDGET_KEYS:
        session_state.pop(key, None)
    # Derived-message attended state is session-only and must not survive a new
    # batch; clear both the dictionary and the per-message toggle widget keys.
    session_state.pop("derivados_atendidos", None)
    for key in list(session_state.keys()):
        if key.startswith(DERIVED_WIDGET_KEY_PREFIX):
            session_state.pop(key, None)
    # A new batch must not inherit which signatures were already published:
    # otherwise a fresh lot's candidate could be blocked as "already sent".
    session_state.pop("telegram_published_times", None)
    session_state["processing_done"] = False
    session_state["llm_results"] = None


def init_session_state():
    """Inicializa variables en session_state para mantener el flujo de la app."""
    if "processing_done" not in st.session_state:
        st.session_state.processing_done = False
    if "llm_results" not in st.session_state:
        st.session_state.llm_results = None


def apply_dashboard_styles():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(ellipse at 5% 0%, rgba(0, 194, 171, 0.08), transparent 34%),
                var(--background-color);
        }
        .block-container {
            max-width: 1440px;
            padding-top: 1.5rem;
            padding-bottom: 3.5rem;
        }
        .communitylab-hero {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2rem;
            overflow: hidden;
            margin: 0 0 1.5rem;
            padding: clamp(1.5rem, 4vw, 3rem);
            color: #F4F7FB;
            background:
                radial-gradient(circle at 0% 0%, rgba(0, 194, 171, 0.45), transparent 22%),
                radial-gradient(circle at 100% 100%, rgba(124, 58, 237, 0.45), transparent 24%),
                linear-gradient(115deg, #0B2D4A, #10243D 68%, #0B2D4A);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            box-shadow: 0 16px 36px rgba(11, 45, 74, 0.16);
        }
        .communitylab-brand {
            display: flex;
            align-items: center;
            gap: 1rem;
            min-width: 0;
        }
        .communitylab-logo-panel {
            display: flex;
            align-items: center;
            width: min(100%, 31rem);
            min-height: 6.5rem;
            padding: 0.65rem 1rem;
            border: 1px solid rgba(255, 255, 255, 0.55);
            border-radius: 14px;
            background: #F4F7FB;
        }
        .communitylab-logo-panel img {
            display: block;
            width: 100%;
            max-height: 6rem;
            object-fit: contain;
        }
        .communitylab-hero-copy {
            max-width: 23rem;
            padding-left: clamp(1rem, 3vw, 2.5rem);
            border-left: 1px solid rgba(244, 247, 251, 0.35);
        }
        .communitylab-hero-copy strong {
            display: block;
            margin-bottom: 0.55rem;
            color: #F4F7FB;
            font-size: 1.05rem;
            line-height: 1.35;
        }
        .communitylab-hero-copy span {
            color: rgba(244, 247, 251, 0.78);
            font-size: 0.84rem;
            line-height: 1.55;
        }
        h2, h3 {
            letter-spacing: -0.025em;
        }
        [data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 5px 18px rgba(0, 0, 0, 0.12);
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-color);
            opacity: 0.7;
        }
        [data-testid="stBaseButton-primary"] {
            color: #0B2D4A;
            border: 0;
            background: #00C2AB;
            box-shadow: 0 5px 14px rgba(11, 45, 74, 0.2);
        }
        [data-testid="stBaseButton-primary"]:hover {
            color: #0B2D4A;
            background: #00AE9A;
        }
        [data-testid="stBaseButton"],
        [data-testid="stDownloadButton"] button {
            border-radius: 10px;
            min-height: 2.7rem;
        }
        [data-testid="stExpander"],
        [data-testid="stAlert"] {
            border-radius: 12px;
        }
        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.45rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.25);
        }
        [data-testid="stTabs"] button[role="tab"] {
            padding: 0.65rem 1rem;
        }
        @media (max-width: 720px) {
            .communitylab-hero {
                align-items: flex-start;
                flex-direction: column;
                gap: 1.25rem;
            }
            .communitylab-hero-copy {
                max-width: none;
                padding-left: 0;
                border-left: 0;
                border-top: 1px solid rgba(244, 247, 251, 0.35);
                padding-top: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header():
    logo_data = base64.b64encode(BRAND_LOGO_PATH.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <header class="communitylab-hero" aria-label="CommunityLab">
            <div class="communitylab-brand">
                <div class="communitylab-logo-panel">
                    <img
                        src="data:image/png;base64,{logo_data}"
                        alt="CommunityLab — Escucha, analiza, impacta"
                    />
                </div>
            </div>
            <div class="communitylab-hero-copy">
                <strong>Transformamos las voces de la comunidad en mejores decisiones.</strong>
                <span>Analiza conversaciones, revisa los activos y decide qué compartir.</span>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="CommunityLab - Panel de Curaduría",
        page_icon=BRAND_ICON_PATH.read_bytes(),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()
    apply_dashboard_styles()

    render_brand_header()
    st.subheader("Panel de curaduría")
    st.caption("Analiza conversaciones de comunidad, revisa los activos y decide qué publicar.")

    st.header("1. Cargar Lote de Interacciones")
    st.write("Sube el archivo con los datos exportados de la comunidad (ej. Slack, Discord, Foro).")

    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        uploaded_file = st.file_uploader("Selecciona un archivo JSON", type=["json"])

    with col2:
        st.write("**O ingresa JSON crudo**")
        raw_json_input = st.text_area("Pega el payload aquí...", height=100)

    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample" / "corrida-completa-gemma.json"
    sample_results = load_sample_results(sample_path)

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
    with st.expander("Opciones de demo combinada", expanded=False):
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
        st.header("2. Activos Generados y Análisis")

        results = st.session_state.llm_results
        summary = results["resumen_comunidad"]
        assets = results["activos_distribucion_generados"]
        storage = results["almacenamiento_oci"]

        st.success(f"Estado del lote: {results['status']}")

        st.subheader("📊 Resumen de la comunidad")
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            with st.container(border=True):
                st.metric(label="Total Interacciones", value=summary["total_interacciones_procesadas"])
        with kpi_col2:
            with st.container(border=True):
                st.metric(label="Sentimiento", value=summary["sentimiento_predominante"])
        with kpi_col3:
            with st.container(border=True):
                st.markdown("**Temas Principales**")
                st.write(", ".join(summary["temas_principales"]))

        st.subheader("🚨 Feedback negativo")
        deriv_col1, deriv_col2 = st.columns(2)
        feedback_negativo = summary.get("feedback_negativo", 0)
        analisis_degradados = summary.get("analisis_degradados", 0)
        with deriv_col1:
            with st.container(border=True):
                st.metric(label="Feedback negativo", value=feedback_negativo)
        with deriv_col2:
            with st.container(border=True):
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

            chart_col1, chart_col2 = st.columns(2, gap="large")
            with chart_col1:
                with st.container(border=True):
                    st.subheader("Distribución de Sentimiento")
                    chart = build_sentiment_pie_chart(distribucion_df)
                    if chart is None:
                        st.info("No hay datos suficientes para mostrar la distribución de sentimiento.")
                    else:
                        st.altair_chart(chart, width="stretch")

            with chart_col2:
                with st.container(border=True):
                    st.subheader("Temas Principales (Top)")
                    chart = build_top_topics_chart(temas_df)
                    if chart is None:
                        st.info("No hay datos suficientes para mostrar temas principales.")
                    else:
                        st.altair_chart(chart, width="stretch")

            with st.container(border=True):
                st.subheader("📦 Activos generados por tipo")
                assets_df = build_assets_summary_df(
                    resumen, results["activos_distribucion_generados"]
                )
                chart = build_assets_chart(assets_df)
                if chart is None:
                    st.info("No hay activos generados para mostrar.")
                else:
                    st.altair_chart(chart, width="stretch")
                st.caption(
                    "Los candidatos de LinkedIn son los publicables; el feedback "
                    "negativo se lista en la pestaña Derivados."
                )

        st.subheader("📝 Edición de Activos de Marketing")
        # The selected candidate drives BOTH tabs: its full post (tab 1) and
        # its own newsletter highlight (tab 2).
        seleccionado = None
        selected_index = 0
        tab1, tab2, tab3, tab4 = st.tabs(
            ["💼 Post LinkedIn", "📰 Newsletter", "❓ Sugerencia FAQ", "🚨 Derivados"]
        )

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
                meta_title, meta_channel, meta_engagement = st.columns([1.4, 1, 1])
                with meta_title:
                    st.caption("Título")
                    st.write(post_view["titulo"])
                with meta_channel:
                    st.caption("Canal recomendado")
                    st.write(post_view["canal_recomendado"])
                with meta_engagement:
                    st.caption("Potencial de engagement")
                    st.write(post_view["potencial_engagement"])

                edit_col, publish_col = st.columns([1.35, 1], gap="large")
                with edit_col:
                    st.info("Revisa y ajusta el copy antes de aprobar.")
                    linkedin_edited = st.text_area(
                        "Contenido del Post:",
                        value=post_view["copy"],
                        height=250,
                        key=f"linkedin_edit_{selected_index}",
                        width="stretch",
                    )
                    linkedin_estado = st.radio(
                        "Estado de curaduría:",
                        options=CURATION_STATUSES,
                        index=0,
                        horizontal=True,
                        key=f"linkedin_estado_{selected_index}",
                    )
                    if linkedin_estado == CURATION_STATUS_REJECTED:
                        st.warning(
                            "⚠️ Post de LinkedIn rechazado: no se incluirá en el paquete "
                            "aprobado ni se podrá publicar en Telegram. Se debe cambiar "
                            "el estado para reconsiderar la decisión."
                        )

                # El mensaje de Telegram sale del post que se está editando: el
                # copy del editor manda y se conserva el autor/relevancia del
                # testimonio seleccionado. La preview y el envío usan el MISMO
                # dict y la MISMA función de formato, así la preview nunca
                # puede mentir sobre lo que se publica.
                candidato_telegram = dict(post_view)
                if seleccionado:
                    candidato_telegram["autor"] = seleccionado.get("autor", "")
                    candidato_telegram["relevancia"] = seleccionado.get("relevancia")
                candidato_telegram["copy"] = linkedin_edited

                # Gate de publicación: el botón sólo se habilita con el post
                # Aprobado Y con una firma que todavía no se haya publicado en
                # esta sesión. La preview de arriba queda siempre visible.
                linkedin_aprobado = linkedin_estado == CURATION_STATUS_APPROVED
                with publish_col:
                    st.subheader("👁️ Vista previa del mensaje de Telegram")
                    st.text(telegram_publish.format_candidate_message(candidato_telegram))

                    # Metadata de curaduría: visible para el humano, FUERA del
                    # mensaje publicado.
                    metadata_line = _curation_metadata_line(candidato_telegram)
                    if metadata_line:
                        st.caption(metadata_line)

                    # El destino se muestra ANTES del click: si falta la
                    # configuración se ve una advertencia accionable en lugar
                    # de una excepción tras el click. El token nunca se muestra.
                    destino = telegram_publish.describe_destination()
                    if destino:
                        st.caption(destino)
                    else:
                        st.warning(
                            "Falta configuración de Telegram: se requieren "
                            "TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el archivo .env "
                            "(ver .env.example)."
                        )

                    # Firma = identidad del candidato + copy editado. Una firma ya
                    # publicada queda marcada en st.session_state: el botón se
                    # deshabilita y un click viejo no puede reenviar.
                    firma = telegram_publish.publish_signature(candidato_telegram)
                    publicadas = st.session_state.setdefault("telegram_published_times", {})
                    hora_envio = publicadas.get(firma)
                    ya_publicado = hora_envio is not None

                    decision = publish_decision(linkedin_aprobado, ya_publicado)

                    if not linkedin_aprobado:
                        st.caption(
                            "El post de LinkedIn debe estar aprobado "
                            "(Estado de curaduría: Aprobado) para publicarlo en Telegram."
                        )

                    if st.button(
                        "📨 Publicar en Telegram",
                        key="telegram_publish_button",
                        disabled=decision != PUBLISH_DECISION_APPROVED,
                    ):
                        # Revalidar ambas condiciones evita enviar con un estado
                        # de curaduría obsoleto o repetir un envío anterior.
                        if decision == PUBLISH_DECISION_NOT_APPROVED:
                            st.warning(
                                "El post de LinkedIn no está aprobado; no se publica "
                                "en Telegram."
                            )
                        elif decision == PUBLISH_DECISION_ALREADY_PUBLISHED:
                            st.caption(f"✅ Publicado a las {hora_envio}")
                        else:
                            try:
                                enviado = telegram_publish.publish_candidate(candidato_telegram)
                            except telegram_publish.TelegramConfigError as exc:
                                st.warning(
                                    f"{exc} Se requieren TELEGRAM_BOT_TOKEN y "
                                    "TELEGRAM_CHAT_ID en el archivo .env "
                                    "(ver .env.example)."
                                )
                            except (ValueError, RuntimeError) as exc:
                                st.error(f"No se pudo publicar en Telegram: {exc}")
                            else:
                                publicadas[firma] = datetime.now().strftime("%H:%M")
                                st.success(
                                    "✅ Publicado en Telegram "
                                    f"({len(enviado)} caracteres enviados)."
                                )

                    if publicadas.get(firma):
                        st.caption(f"✅ Publicado a las {publicadas[firma]}")
            else:
                st.info("No se generó un post de LinkedIn para este lote.")
                linkedin_edited = ""
                linkedin_estado = CURATION_STATUS_PENDING

        with tab2:
            newsletter = assets["destaque_newsletter_semanal"]
            newsletter = merged_newsletter(newsletter, seleccionado)
            if newsletter:
                st.write(f"**Sección:** {newsletter['seccion']}")
                st.write(f"**Titular:** {newsletter['titular']}")
                st.info("Resumen para incluir en el próximo correo semanal.")
                newsletter_edited = st.text_area("Contenido Newsletter:", value=newsletter["resumen"], height=200, key=f"news_edit_{selected_index}", width="stretch")
                newsletter_estado = st.radio(
                    "Estado de curaduría:",
                    options=CURATION_STATUSES,
                    index=0,
                    horizontal=True,
                    key=f"news_estado_{selected_index}",
                )
                if newsletter_estado == CURATION_STATUS_REJECTED:
                    st.warning(
                        "⚠️ Newsletter rechazada: no se incluirá en el paquete "
                        "aprobado. Se debe cambiar el estado para reconsiderar la "
                        "decisión."
                    )
            else:
                st.info("No se generó un destaque para la newsletter semanal.")
                newsletter_edited = ""
                newsletter_estado = CURATION_STATUS_PENDING

        with tab3:
            temas_faq = assets.get("temas_faq") or []
            sugerencia = assets.get("sugerencia_contenido_faq")

            # Render consolidated themes when available; fall back to the legacy
            # single suggestion for old outputs that lack `temas_faq`.
            if temas_faq:
                st.write(f"**{len(temas_faq)} tema(s) de FAQ detectado(s).**")
                for numero, tema in enumerate(temas_faq, start=1):
                    titulo = str(tema.get("tema") or "")
                    respuesta = str(tema.get("respuesta") or titulo)
                    representativa = str(tema.get("pregunta_representativa") or "")
                    total = int(tema.get("total_preguntas") or 0)
                    with st.container(border=True):
                        st.write(f"**{numero}. {titulo}**")
                        if representativa:
                            st.write(f"- {representativa}")
                        if total > 0:
                            st.caption(
                                f"{total} pregunta(s) relacionada(s) con este tema."
                            )
                        st.info("Respuesta sugerida:")
                        st.write(respuesta)
                        st.caption(
                            f"Origen: {tema.get('origen', '')} · "
                            f"Estado: {tema.get('status', '')}"
                        )
            elif sugerencia:
                st.write(f"**Origen:** {sugerencia['origen']}")
                st.write(f"**Estado:** {sugerencia['status']}")
                st.info("Pregunta frecuente detectada automáticamente para la base de conocimiento.")

            # The approval editor always follows the published single suggestion.
            # If the pipeline produced themes but no explicit suggestion, the first
            # theme is the suggestion; this keeps the package backward compatible.
            sugerencia = sugerencia or (temas_faq[0] if temas_faq else None)
            if sugerencia:
                faq_edited = st.text_area(
                    "Entrada FAQ:",
                    value=sugerencia.get("respuesta") or sugerencia["tema"],
                    height=200,
                    key="faq_edit",
                    width="stretch",
                )
                faq_estado = st.radio(
                    "Estado de curaduría:",
                    options=CURATION_STATUSES,
                    index=0,
                    horizontal=True,
                    key="faq_estado",
                )
                if faq_estado == CURATION_STATUS_REJECTED:
                    st.warning(
                        "⚠️ Sugerencia FAQ rechazada: no se incluirá en el paquete "
                        "aprobado. Se debe cambiar el estado para reconsiderar la "
                        "decisión."
                    )
            else:
                st.info("No se detectó una pregunta frecuente para este lote.")
                faq_edited = ""
                faq_estado = CURATION_STATUS_PENDING

            # List-only visibility of the questions that did NOT map to a FAQ
            # theme (orphaned). The themed questions already appear inside each
            # theme above, so this list avoids repeating them.
            candidatos_faq = assets.get("candidatos_faq") or []
            if candidatos_faq:
                st.caption(
                    f"{len(candidatos_faq)} preguntas detectadas sin tema claro "
                    "(no mapeadas a ningún tema FAQ)."
                )
                for numero, candidato in enumerate(candidatos_faq, start=1):
                    texto = str(candidato.get("texto_original") or "").strip()
                    autor = str(candidato.get("autor") or "").strip()
                    canal = str(candidato.get("canal") or "").strip()
                    try:
                        relevancia = f"{float(candidato.get('relevancia') or 0.0):.0%}"
                    except (TypeError, ValueError):
                        relevancia = str(candidato.get("relevancia"))
                    st.write(f"**{numero}.** {texto}")
                    st.caption(
                        " · ".join(
                            parte
                            for parte in (autor, canal, f"Relevancia: {relevancia}")
                            if parte
                        )
                    )

        with tab4:
            mensajes_derivados = assets.get("mensajes_derivados") or []
            if mensajes_derivados:
                st.write(
                    f"{len(mensajes_derivados)} mensaje(s) derivado(s) a revisión humana. "
                    "El estado 'atendido' es solo para esta sesión."
                )
                for entry in build_derivados_entries(mensajes_derivados, st.session_state):
                    key = entry["key"]
                    widget_key = f"{DERIVED_WIDGET_KEY_PREFIX}{key}"
                    col_text, col_toggle = st.columns([3, 1], gap="large")
                    with col_text:
                        st.write(f"**{entry['autor']}** · {entry['canal']}")
                        st.write(entry["texto_original"])
                        st.caption(
                            f"Motivo: {entry['razon']} · "
                            f"Confianza: {entry['confianza']:.0%}"
                        )
                    with col_toggle:
                        atendido = st.checkbox(
                            "Atendido",
                            value=entry["atendido"],
                            key=widget_key,
                        )
                        if atendido != entry["atendido"]:
                            set_atendido(st.session_state, key, atendido)
            else:
                st.info("No hay mensajes derivados a revisión humana en este lote.")

        # Un activo entra al paquete sólo si está Aprobado y su texto editado
        # no está vacío. Pendiente y Rechazado quedan afuera.
        payload_to_save = {
            "linkedin": (
                linkedin_edited
                if linkedin_estado == CURATION_STATUS_APPROVED and linkedin_edited.strip()
                else None
            ),
            "newsletter": (
                newsletter_edited
                if newsletter_estado == CURATION_STATUS_APPROVED and newsletter_edited.strip()
                else None
            ),
            "faq": (
                faq_edited
                if faq_estado == CURATION_STATUS_APPROVED and faq_edited.strip()
                else None
            ),
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

        rejected_count = sum(
            estado == CURATION_STATUS_REJECTED
            for estado in (linkedin_estado, newsletter_estado, faq_estado)
        )

        if st.button("Aprobar activos seleccionados", type="primary", width="stretch"):
            if not any(value and value.strip() for value in payload_to_save.values()):
                st.warning("⚠️ Se debe aprobar al menos un activo para poder guardarlo.")
            else:
                approved_count = sum(bool(value and value.strip()) for value in payload_to_save.values())
                approved_label = "activo aprobado" if approved_count == 1 else "activos aprobados"
                if rejected_count:
                    rejected_label = (
                        "activo rechazado" if rejected_count == 1 else "activos rechazados"
                    )
                    rejected_verb = "queda" if rejected_count == 1 else "quedan"
                    resumen_rechazados = (
                        f"{rejected_count} {rejected_label} {rejected_verb} "
                        "fuera del paquete. "
                    )
                else:
                    resumen_rechazados = ""
                st.info(
                    f"{approved_count} {approved_label} en esta sesión. "
                    f"{resumen_rechazados}"
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
