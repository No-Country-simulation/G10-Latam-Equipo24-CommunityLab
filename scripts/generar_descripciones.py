# Script para añadir descripciones técnicas a las fichas
# Ejecutar en la carpeta del proyecto

import re

descripciones = {
    "HU-S1-001": {
        "que_hace": "Crear las clases Python que representan los datos del sistema (mensajes, sentimientos, decisiones, activos)",
        "que_funciona": "Es la base de todo el sistema. Sin modelos correctos, ningún módulo puede funcionar porque no sabe qué datos esperar",
        "donde": "src/domain/models.py"
    },
    "HU-S1-002": {
        "que_hace": "Definir los contratos abstractos (interfaces) que cada módulo debe cumplir",
        "que_funciona": "Garantiza que todos los módulos se comuniquen de la misma manera. Si un módulo cumple la interfaz, funciona con cualquier otro",
        "donde": "src/domain/interfaces.py"
    },
    "HU-S1-003": {
        "que_hace": "Crear el cargador de archivos JSON que lee el formato de entrada del sistema",
        "que_funciona": "Es la puerta de entrada de datos. Sin esto no hay nada que analizar",
        "donde": "src/ingest/input_loader.py"
    },
    "HU-S1-004": {
        "que_hace": "Crear el normalizador que convierte JSON crudo a objetos Message del sistema",
        "que_funciona": "Permite que datos de Discord, Slack o API se conviertan al formato interno. Unifica todas las fuentes",
        "donde": "src/ingest/normalizer.py"
    },
    "HU-S1-005": {
        "que_hace": "Configurar GitHub Actions para que tests y linting corran automáticamente",
        "que_funciona": "Detecta errores antes de que entren al código principal. Protege la calidad",
        "donde": ".github/workflows/ci.yml"
    },
    "HU-S1-006": {
        "que_hace": "Crear requirements.txt, .env.example, .gitignore e instrucciones de setup",
        "que_funciona": "Permite que cualquier miembro del equipo instale y configure el proyecto en minutos",
        "donde": "Raíz del proyecto (requirements.txt, .env.example, .gitignore)"
    },
    "HU-S1-007": {
        "que_hace": "Crear la estructura de carpetas con __init__.py en cada módulo",
        "que_funciona": "Define dónde vive cada parte del código. Es el esqueleto del proyecto",
        "donde": "src/, tests/, data/, docs/, .github/"
    },
    "HU-S1-008": {
        "que_hace": "Crear la documentación técnica con diagramas y descripciones",
        "que_funciona": "Explica la arquitectura al equipo y al jurado. Es la carta de presentación técnica",
        "donde": "docs/arquitectura.md, docs/analisis_datasets.md, docs/historias-de-usuario.md"
    },
    "HU-S2-001": {
        "que_hace": "Implementar el análisis de sentimiento usando Google Gemini API",
        "que_funciona": "Detecta si un mensaje es positivo, negativo o neutro. Permite identificar testimonios y riesgos",
        "donde": "src/analysis/sentiment.py"
    },
    "HU-S2-002": {
        "que_hace": "Implementar la clasificación de mensajes en categorías usando Gemini",
        "que_funciona": "Clasifica cada mensaje en duda_tecnica, testimonio, feedback, etc. Es la base para generar el contenido correcto",
        "donde": "src/analysis/categorization.py"
    },
    "HU-S2-003": {
        "que_hace": "Implementar la evaluación de relevancia para marketing usando Gemini",
        "que_funciona": "Puntúa qué mensaje vale la pena publicar. Filtra contenido basura del contenido valioso",
        "donde": "src/analysis/relevance.py"
    },
    "HU-S2-004": {
        "que_hace": "Crear el orquestador que ejecute los 3 análisis en orden",
        "que_funciona": "Coordina sentimiento + categorización + relevancia en un solo paso. Es el corazón del pipeline de análisis",
        "donde": "src/analysis/orchestrator.py"
    },
    "HU-S2-005": {
        "que_hace": "Crear el motor de decisiones con reglas de negocio",
        "que_funciona": "Decide si un mensaje debe ser LinkedIn, FAQ, newsletter o descartarse. Es el cerebro del sistema",
        "donde": "src/decisions/engine.py"
    },
    "HU-S2-006": {
        "que_hace": "Crear el detector de miembros en riesgo",
        "que_funciona": "Alerta cuando un usuario muestra sentimiento negativo recurrente. Permite intervención temprana",
        "donde": "src/decisions/member_risk.py"
    },
    "HU-S2-007": {
        "que_hace": "Crear el detector de dudas recurrentes",
        "que_funciona": "Identifica preguntas repetidas para generar FAQs automáticos. Reduce trabajo manual",
        "donde": "src/decisions/recurring_topics.py"
    },
    "HU-S2-008": {
        "que_hace": "Configurar conexión con Gemini API y centralizar prompts",
        "que_funciona": "Todos los módulos de IA usan Gemini. Este archivo asegura que la conexión funcione y los prompts estén organizados",
        "donde": ".env (GEMINI_API_KEY), src/prompts/templates.py"
    },
    "HU-S3-001": {
        "que_hace": "Crear el generador de posts de LinkedIn a partir de testimonios",
        "que_funciona": "Genera contenido profesional para LinkedIn automáticamente. El activo de marketing más visible",
        "donde": "src/generators/linkedin.py"
    },
    "HU-S3-002": {
        "que_hace": "Crear el generador de contenido para newsletters",
        "que_funciona": "Genera contenido semanal para mantener informada a la comunidad",
        "donde": "src/generators/newsletter.py"
    },
    "HU-S3-003": {
        "que_hace": "Crear el generador de preguntas frecuentes (FAQ)",
        "que_funciona": "Genera FAQs a partir de dudas técnicas recurrentes. Crea base de conocimiento automática",
        "donde": "src/generators/faq.py"
    },
    "HU-S3-004": {
        "que_hace": "Crear el generador de testimonios formateados",
        "que_funciona": "Formatea experiencias positivas como testimonios para redes sociales y web",
        "donde": "src/generators/testimonial.py"
    },
    "HU-S3-005": {
        "que_hace": "Crear el pipeline completo que una ingesta, análisis, decisiones y generadores",
        "que_funciona": "Es el punto de entrada principal. Recibe JSON y retorna JSON. Demuestra que todo funciona junto",
        "donde": "src/pipeline.py"
    },
    "HU-S3-006": {
        "que_hace": "Crear validación del JSON de entrada antes de procesar",
        "que_funciona": "Evita que datos malformados rompan el pipeline. Valida estructura y campos",
        "donde": "src/ingest/validator.py"
    },
    "HU-S4-001": {
        "que_hace": "Implementar el cliente de conexión con Oracle Cloud Infrastructure",
        "que_funciona": "Es la base para todo lo relacionado con OCI. Sin conexión no hay storage",
        "donde": "src/oci/client.py"
    },
    "HU-S4-002": {
        "que_hace": "Implementar operaciones de subida y descarga de archivos en OCI",
        "que_funciona": "Guarda activos generados (posts, FAQs) en la nube. Cumple el requisito obligatorio de OCI",
        "donde": "src/oci/storage.py"
    },
    "HU-S4-003": {
        "que_hace": "Crear el dashboard de métricas en Streamlit con gráficos",
        "que_funciona": "Es la pantalla principal donde el community manager ve el estado de la comunidad",
        "donde": "src/interface/app.py, src/interface/pages/1_dashboard.py"
    },
    "HU-S4-004": {
        "que_hace": "Crear el panel para aprobar/editar/rechazar activos generados",
        "que_funciona": "Permite al community manager controlar la calidad antes de publicar. Es el control de calidad",
        "donde": "src/interface/pages/2_curaduria.py"
    },
    "HU-S4-005": {
        "que_hace": "Crear el panel de alertas de riesgo y dudas recurrentes",
        "que_funciona": "Muestra problemas que necesitan atención inmediata. Es el sistema de alertas",
        "donde": "src/interface/pages/3_alertas.py"
    },
    "HU-S4-006": {
        "que_hace": "Crear el API endpoint que recibe JSON y retorna JSON procesado",
        "que_funciona": "Permite integración con sistemas externos. Es la interfaz programática del sistema",
        "donde": "src/api/app.py"
    },
    "HU-S5-001": {
        "que_hace": "Desplegar la aplicación en OCI Compute y dejarla corriendo",
        "que_funciona": "Cumple el requisito obligatorio de despliegue en OCI. Hace la app accesible al jurado",
        "donde": "OCI Compute Instance (VM.Standard.E2.1.Micro)"
    },
    "HU-S5-002": {
        "que_hace": "Finalizar toda la documentación técnica del proyecto",
        "que_funciona": "Es la documentación que el jurado y el equipo usarán. Arquitectura, API, despliegue",
        "donde": "docs/ (arquitectura.md, api.md, deploy.md, pipeline.md)"
    },
    "HU-S5-003": {
        "que_hace": "Grabar un video demostrativo del sistema funcionando",
        "que_funciona": "Es la forma de mostrar el proyecto al jurado sin estar presente. Muestra todas las funcionalidades",
        "donde": "YouTube (no público) — grabación de pantalla"
    },
    "HU-S5-004": {
        "que_hace": "Preparar la presentación final para el jurado",
        "que_funciona": "Es la defensa verbal del proyecto. Máximo 15 minutos",
        "donde": "Google Slides o similar"
    },
    "HU-S5-005": {
        "que_hace": "Crear un dataset de prueba con 50 mensajes diversos",
        "que_funciona": "Permite demostrar todas las funcionalidades con datos reales. Es el input de la demo",
        "donde": "data/raw/communitylab-sample.json"
    },
    "HU-S5-006": {
        "que_hace": "Probar todo el sistema end-to-end y corregir bugs críticos",
        "que_funciona": "Garantiza que la demo no falle. Es la última línea de defensa",
        "donde": "Todo el código — testing completo"
    },
    "HU-S5-007": {
        "que_hace": "Crear webhooks para notificaciones cuando hay resultados o alertas",
        "que_funciona": "Notifica al equipo cuando algo importante pasa. Integración opcional con Discord/Slack",
        "donde": "src/notifications/webhook.py"
    }
}

print(f"Total de fichas con descripción técnica: {len(descripciones)}")
for k, v in descripciones.items():
    print(f"{k}: {v['que_funciona'][:50]}...")
