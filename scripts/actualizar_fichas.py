import os
import re

# Build absolute path
base_dir = r"C:\Users\WIN10\Desktop\Hakaton ONE\communitylab"
fichas_path = os.path.join(base_dir, "docs", "fichas-historias-usuario.md")

if not os.path.exists(fichas_path):
    print(f"ERROR: File not found: {fichas_path}")
    exit(1)

print(f"Processing: {fichas_path}")

with open(fichas_path, "r", encoding="utf-8") as f:
    content = f.read()

DESCRIPCIONES = {
    "HU-S1-001": ("Crear las clases Python que representan los datos del sistema",
                   "Base de todo el sistema. Sin modelos, ningun modulo funciona",
                   "src/domain/models.py"),
    "HU-S1-002": ("Definir contratos abstractos que cada modulo debe cumplir",
                   "Garantiza que todos los modulos se comuniquen igual",
                   "src/domain/interfaces.py"),
    "HU-S1-003": ("Crear el cargador de archivos JSON de entrada",
                   "Puerta de entrada de datos. Sin esto nada funciona",
                   "src/ingest/input_loader.py"),
    "HU-S1-004": ("Crear el normalizador de JSON a objetos Message",
                   "Unifica datos de Discord/Slack/API al formato interno",
                   "src/ingest/normalizer.py"),
    "HU-S1-005": ("Configurar GitHub Actions para tests y linting automaticos",
                   "Detecta errores antes de que entren al codigo",
                   ".github/workflows/ci.yml"),
    "HU-S1-006": ("Crear requirements.txt, .env.example, .gitignore",
                   "Permite instalar y configurar el proyecto rapido",
                   "raiz del proyecto"),
    "HU-S1-007": ("Crear estructura de carpetas con __init__.py",
                   "Define donde vive cada parte del codigo",
                   "src/, tests/, data/, docs/"),
    "HU-S1-008": ("Crear documentacion tecnica con diagramas",
                   "Explica arquitectura al equipo y jurado",
                   "docs/arquitectura.md"),
    "HU-S2-001": ("Implementar analisis de sentimiento con Gemini",
                   "Detecta si mensaje es positivo/negativo/neutral",
                   "src/analysis/sentiment.py"),
    "HU-S2-002": ("Implementar clasificacion de mensajes en categorias",
                   "Clasifica en duda_tecnica, testimonio, feedback, etc",
                   "src/analysis/categorization.py"),
    "HU-S2-003": ("Implementar evaluacion de relevancia",
                   "Puntua que mensaje vale la pena publicar",
                   "src/analysis/relevance.py"),
    "HU-S2-004": ("Crear orquestador que ejecute 3 analisis en orden",
                   "Coordina sentimiento + categorizacion + relevancia",
                   "src/analysis/orchestrator.py"),
    "HU-S2-005": ("Crear motor de decisiones con reglas",
                   "Decide si mensaje es LinkedIn, FAQ, newsletter, etc",
                   "src/decisions/engine.py"),
    "HU-S2-006": ("Crear detector de miembros en riesgo",
                   "Alerta sobre sentimiento negativo recurrente",
                   "src/decisions/member_risk.py"),
    "HU-S2-007": ("Crear detector de dudas recurrentes",
                   "Identifica preguntas repetidas para FAQs",
                   "src/decisions/recurring_topics.py"),
    "HU-S2-008": ("Configurar conexion Gemini y prompts",
                   "Centraliza conexion IA y plantillas de prompts",
                   ".env, src/prompts/templates.py"),
    "HU-S3-001": ("Crear generador de posts LinkedIn",
                   "Genera contenido profesional automaticamente",
                   "src/generators/linkedin.py"),
    "HU-S3-002": ("Crear generador de newsletters",
                   "Genera contenido semanal para comunidad",
                   "src/generators/newsletter.py"),
    "HU-S3-003": ("Crear generador de FAQs",
                   "Genera FAQs desde dudas tecnicas",
                   "src/generators/faq.py"),
    "HU-S3-004": ("Crear generador de testimonios",
                   "Formatea experiencias como testimonios",
                   "src/generators/testimonial.py"),
    "HU-S3-005": ("Crear pipeline completo end-to-end",
                   "Recibe JSON, retorna JSON. Todo junto",
                   "src/pipeline.py"),
    "HU-S3-006": ("Crear validacion del JSON de entrada",
                   "Evita que datos malformados rompan pipeline",
                   "src/ingest/validator.py"),
    "HU-S4-001": ("Implementar cliente OCI",
                   "Base para todo lo relacionado con OCI",
                   "src/oci/client.py"),
    "HU-S4-002": ("Implementar storage en OCI",
                   "Guarda activos en la nube. Requisito obligatorio",
                   "src/oci/storage.py"),
    "HU-S4-003": ("Crear dashboard metricas Streamlit",
                   "Pantalla principal del community manager",
                   "src/interface/app.py"),
    "HU-S4-004": ("Crear panel de curaduria",
                   "Aprobar/editar/rechazar antes de publicar",
                   "src/interface/pages/2_curaduria.py"),
    "HU-S4-005": ("Crear panel de alertas",
                   "Muestra problemas que necesitan atencion",
                   "src/interface/pages/3_alertas.py"),
    "HU-S4-006": ("Crear API endpoint JSON",
                   "Integracion con sistemas externos",
                   "src/api/app.py"),
    "HU-S5-001": ("Desplegar en OCI Compute",
                   "Requisito obligatorio de despliegue OCI",
                   "OCI Compute"),
    "HU-S5-002": ("Finalizar documentacion tecnica",
                   "Documentacion para jurado y equipo",
                   "docs/"),
    "HU-S5-003": ("Grabar video demostrativo",
                   "Muestra proyecto al jurado",
                   "YouTube no publico"),
    "HU-S5-004": ("Preparar presentacion final",
                   "Defensa verbal del proyecto",
                   "Google Slides"),
    "HU-S5-005": ("Crear dataset prueba 50 mensajes",
                   "Datos para demostrar todas funcionalidades",
                   "data/raw/communitylab-sample.json"),
    "HU-S5-006": ("Probar end-to-end y corregir bugs",
                   "Garantiza que demo no falle",
                   "Todo el codigo"),
    "HU-S5-007": ("Crear webhooks notificaciones",
                   "Notifica resultados y alertas al equipo",
                   "src/notifications/webhook.py"),
}

# Pattern: find each ficha and insert description after acceptance criteria
count = 0
for hu_id, (qh, qf, donde) in DESCRIPCIONES.items():
    # Find the ficha by its ID
    pattern = r"(### FICHA " + hu_id + r".*?Criterios de aceptacion:\n(?:.*\n)*?- \[\] [^\n]*\n)"
    
    desc_section = (
        "\n"
        "**Descripcion tecnica:**\n"
        f"- **Que hacer:** {qh}\n"
        f"- **Que funcion cumple:** {qf}\n"
        f"- **Donde hacerlo:** `{donde}`\n"
    )
    
    def replace_fn(match):
        return match.group(1) + desc_section
    
    new_content, replacements = re.subn(pattern, replace_fn, content, count=1, flags=re.DOTALL)
    
    if replacements == 1:
        content = new_content
        count += 1
    else:
        print(f"Warning: Could not find {hu_id}")

with open(fichas_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Done! Updated {count} fichas with technical descriptions")
