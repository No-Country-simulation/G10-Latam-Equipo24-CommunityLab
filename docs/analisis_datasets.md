# 📊 ANÁLISIS DE DATASETS REALES — CommunityLab

> **Objetivo:** Determinar la viabilidad de obtener datos reales de comunidades digitales para el MVP
> **Criterios evaluados:** Legalidad, dificultad técnica, tamaño, idioma, relevancia para el sector MarTech

---

## 🚦 RESUMEN EJECUTIVO

| Opción | Dificultad | Legalidad | Tiempo estimado | Viabilidad MVP |
|--------|-----------|-----------|-----------------|----------------|
| 1. Hugging Face (Discord listo) | 🟢 Fácil | ✅ Alta | 10 min | ✅ RECOMENDADO |
| 2. Kaggle (Reddit con sentimiento) | 🟢 Fácil | ✅ Alta | 15 min | ✅ RECOMENDADO |
| 3. GitHub Issues dataset | 🟢 Fácil | ✅ Alta | 15 min | ✅ RECOMENDADO |
| 4. Kaggle (Coursera reviews) | 🟢 Fácil | ✅ Media | 20 min | ✅ BUENO |
| 5. Web scraping Discord API | 🟡 Media | ⚠️ Riesgoso | 3-6 horas | ⚠️ NO |
| 6. Reddit API (PRAW) | 🟡 Media | ✅ Con cuidado | 2-4 horas | ⚠️ ALTERNATIVO |
| 7. Web scraping Coursera | 🟠 Difícil | ⚠️ Riesgoso | 4-8 horas | ❌ NO |
| 8. Nuestra propia comunidad | 🟢 Fácil | ✅ Perfecto | Variable | ✅ IDEAL |

---

## ✅ OPCIÓN 1: Hugging Face — Discord Dialogues

### 🟢 DIFICULTAD: MUY FÁCIL (descarga directa)

**Dataset:** `mooaoeu/Discord-Dialogues`
**URL:** https://huggingface.co/datasets/mooaoeu/Discord-Dialogues

| Atributo | Valor |
|----------|-------|
| Tamaño | 7.3 millones de intercambios / 16M turns / 139M palabras |
| Formato | ChatML-friendly |
| Idioma | Principalmente inglés, con otros idiomas |
| Licencia | Pública (adhiere a ToS de Discord) |
| Anonimización | ✅ Sí |
| Contenido | Conversaciones humanas reales de Discord |
| Filtrado | Sin spam, bots, contenido dañino, links |

**Cómo obtenerlo:**
```python
# pip install datasets
from datasets import load_dataset

ds = load_dataset("mooaoeu/Discord-Dialogues")
# → Streaming para evitar descargar todo
```

**Ventajas:**
- Datos REALES de comunidades Discord ✅
- Ya anonimizado y limpio ✅
- Descarga instantánea ✅
- Puedes usar sample pequeño (100-500 mensajes) para el MVP

**Desventajas:**
- No tiene canales/categorías (solo texto)
- Principalmente inglés (no portugués como el ejemplo del PDF)
- Son conversaciones de 2 personas, no mensajes individuales

**Grado de dificultad: 1/5** | **Tiempo: 10 minutos**

---

## ✅ OPCIÓN 2: Kaggle — Reddit con Sentimiento

### 🟢 DIFICULTAD: FÁCIL (descarga directa)

**Dataset:** `Reddit Comments Sentiment Dataset`
**URL:** https://www.kaggle.com/datasets/bornaetminan/reddit-comments-sentiment-dataset

| Atributo | Valor |
|----------|-------|
| Tamaño | Grande (100K+ comentarios) |
| Formato | CSV |
| Idioma | Inglés |
| Licencia | CC BY 4.0 |
| Columnas | `clean_text`, `label` (positivo/neutral/negativo), `subreddit`, `created_at`, `username` |

**Ventajas:**
- Ya tiene etiquetas de sentimiento ✅
- Con subreddit (equivalente a canal) ✅
- Ideal para validar nuestro análisis de sentimiento contra el ground truth

**Cómo obtenerlo:**
```python
# pip install kaggle
kaggle datasets download -d bornaetminan/reddit-comments-sentiment-dataset
```

**Grado de dificultad: 1/5** | **Tiempo: 15 minutos**

---

## ✅ OPCIÓN 3: Hugging Face — GitHub Issues/HuggingFace

### 🟢 DIFICULTAD: FÁCIL (descarga directa)

**Dataset:** `helmo/github-issues`
**URL:** https://huggingface.co/datasets/helmo/github-issues

| Atributo | Valor |
|----------|-------|
| Tamaño | 7,540 issues/PRs del repo huggingface/datasets |
| Formato | JSON estructurado |
| Idioma | Inglés |
| Licencia | Apache 2.0 |
| Campos | number, title, body, state, labels, comments, reacciones, autor |

**Ventajas:**
- Tiene **Estructura REAL de comunidad**: issues, comentarios, labels ✅
- Reacciones (+1, -1, corazón) = señales de engagement ✅
- Se parece MUCHO al formato del ejemplo del PDF (canal, autor, texto) ✅
- Perfecto para demostrar "dudas técnicas" y "feedback"

**Desventajas:**
- Solo de 1 repo (huggingface/datasets)
- No tiene "testimonios de éxito" (es más soporte técnico)

**Grado de dificultad: 1/5** | **Tiempo: 10 minutos**

---

## ✅ OPCIÓN 4: Kaggle — Coursera Reviews (para testimonios)

### 🟢 DIFICULTAD: FÁCIL (descarga directa)

**Dataset:** `100K Coursera's Course Reviews Dataset`
**URL:** https://www.kaggle.com/datasets/septa97/100k-courseras-course-reviews-dataset

| Atributo | Valor |
|----------|-------|
| Tamaño | 100K+ reviews |
| Formato | TSV |
| Idioma | Mixto (mayoría inglés, hay otros) |
| Columnas | Review text + Label (1-5 estrellas) |

**Ventajas:**
- Reviews REALES de cursos ✅
- Ya tiene labels de sentimiento (por rating) ✅
- MUY parecido a "feedback de cursos" del contexto del proyecto ✅
- Ideal para el caso de uso: "testimonios de estudiantes"

**Desventajas:**
- Reviews en su mayoría en inglés
- No es conversación de comunidad (es review individual)

**Grado de dificultad: 1/5** | **Tiempo: 20 minutos**

---

## ⚠️ OPCIÓN 5: Web Scraping Discord API — NO RECOMENDADO

### 🟡 DIFICULTAD: MEDIA | ⚠️ LEGALIDAD: RIESGOSA

**Discord Developer Policy DICE EXPLÍCITAMENTE:**

> *"You may not mine or scrape any data, content, or information available on or through Discord services"*
> *"Don't use the services to... scraping our services without our written consent"*

**Riesgos legales:**
- ❌ Discord Prohíbe EL SCRAPING (incluso con API autenticada)
- ❌ Si el jurado pregunta "¿cómo obtuvieron los datos?" y dices "scraping de Discord", puede arruinar la presentación
- ⚠️ El dataset de Discord-Unveiled (2B mensajes) TUVIERON SUSPENDIDA SU DESCARGA precisamente por pedido de los organizadores de ICWSM — señal clara de que esto es terreno minado

**Solo sería permisible si:**
1. Son miembros/administradores de su PROPIA comunidad Discord
2. Exportan los datos manualmente (export de Discord)
3. Usan los nombres de los canales y mensajes de SU servidor

**Grado de dificultad técnico: 2/5** | **Riesgo legal: ALTO** | **Tiempo: 3-6 horas**

---

## ⚠️ OPCIÓN 6: Reddit API (PRAW) — PERMISIBLE CON CUIDADO

### 🟡 DIFICULTAD: MEDIA | ✅ CON RESTRICCIONES

**Reddit API SÍ ES legal** para uso no comercial con límites de rate:

**Cómo obtenerlo:**
```python
# pip install praw
import praw

reddit = praw.Reddit(
    client_id="TU_ID",
    client_secret="TU_SECRET",
    user_agent="communitylab/0.1 by tu_usuario"
)

# Buscar en r/learnprogramming posts recientes
subreddit = reddit.subreddit("learnprogramming")
for post in subreddit.hot(limit=50):
    print(post.title, post.selftext)
```

**Ventajas:**
- Legal (Reddit permite API con autenticación) ✅
- Comunidades tech reales (r/learnprogramming, r/datascience, etc.) ✅
- Obtienes posts + comments + upvotes ✅

**Desventajas:**
- Rate limit (100 consultas/minuto)
- Necesitas registrar la app en Reddit (5 min)
- Los datos en inglés

**Grado de dificultad: 2/5** | **Riesgo legal: BAJO (con app oficial)** | **Tiempo: 2-4 horas**

---

## ✅ OPCIÓN 7: Kaggle — Stack Overflow Questions

### 🟢 DIFICULTAD: FÁCIL

**Dataset:** `Stack Overflow Programming Questions Dataset (2020-2025)`
**URL:** https://www.kaggle.com/datasets/kutayahin/stackoverflow-programming-questions-2020-2025

| Atributo | Valor |
|----------|-------|
| Tamaño | Grandes volúmenes de preguntas |
| Formato | CSV |
| Idioma | Inglés |
| Columnas | Preguntas, respuestas, tags, votos |

**Ventajas:**
- Preguntas técnicas REALES con tags ✅
- Perfecto para el caso "duda técnica → FAQ" ✅
- Votos = engagement ✅

**Grado de dificultad: 1/5** | **Tiempo: 15 minutos**

---

## ❌ OPCIÓN 8: Web Scraping Coursera/Udemy — NO RECOMENDADO

### 🟠 DIFICULTAD: ALTA | ⚠️ RIESGOSO

- Coursera **prohíbe scraping** en sus ToS
- Muchos sitios usan Cloudflare (anti-bot)
- Riesgo de IP blocking
- El dataset ya existe en Kaggle (no necesitas scrapear)

**Grado de dificultad: 4/5** | **Riesgo legal: ALTO** | **Tiempo: 4-8 horas**

---

## 💎 OPCIÓN 9: SU PROPIA COMUNIDAD — IDEAL

### 🟢 DIFICULTAD: FÁCIL | ✅ 100% LEGAL

**Si el equipo (o la institución) tiene:**
- Un Discord de la formación ONE
- Un grupo de WhatsApp/Telegram de estudiantes
- Formularios de feedback de cursos

**Pueden:**
1. **Pedir permiso** a los admin (y a los miembros mediante consentimiento)
2. **Exportar los mensajes** (Discord tiene export nativo: Settings → Export Data)
3. **Anonimizar** los nombres y datos personales
4. Usarlos directamente

**Ventajas:**
- Datos 100% relevantes al contexto del hackathon ✅
- Sin problemas legales ✅
- Pueden contar la historia: "Convertimos nuestra propia comunidad en valor" ✅
- El jurado VERÁ un caso real ✅

---

## 🎯 RECOMENDACIÓN FINAL — ESTRATEGIA HÍBRIDA

Para el MVP, combinar **2-3 fuentes** para cubrir los casos de uso:

```
┌─────────────────────────────────────────────────────────────────┐
│  CASO DE USO DEL PDF            →  FUENTE DE DATOS              │
├─────────────────────────────────────────────────────────────────┤
│  Testimonios de éxito/empleo    →  Kaggle: Coursera Reviews      │
│  (Mariana Souza: contratada)       (reviews positivas 4-5★)      │
│                                                                  │
│  Dudas técnicas (Lucas:         →  HuggingFace: GitHub Issues    │
│  nodos condicionales LangGraph)    (issues con dudas reales)      │
│                                                                  │
│  Mensajes de comunidad Discord  →  ¡SU PROPIO DISCORD!           │
│  (si tienen acceso)                (export + consentimiento)      │
│                                  →  FALLBACK: HF Discord Dialogues│
│                                                                  │
│  Análisis de sentimiento        →  Kaggle: Reddit Comments       │
│  (validación del pipeline)         (ya tiene labels para validar) │
└─────────────────────────────────────────────────────────────────┘
```

### 🎬 Plan de acción (1 día de trabajo del Data Analyst)

| Paso | Acción | Responsable | Tiempo |
|------|--------|-------------|--------|
| 1 | Crear cuenta en Kaggle + descargar Coursera Reviews | DA1 | 30 min |
| 2 | Descargar HF GitHub Issues + filtrar dudas técnicas | DA2 | 30 min |
| 3 | Descargar HF Discord Dialogues + tomar sample de 200 msgs | DA2 | 30 min |
| 4 | Preguntar al equipo si alguno tiene acceso a un Discord de formación | Tech Lead | 10 min |
| 5 | Convertir a formato estándar del proyecto + anonimizar | DA1 + DA2 | 2-3 horas |
| 6 | Documentar la procedencia y licencia de cada dataset | DA1 + DA2 | 1 hora |

### 🚨 RECORDAR PARA LA DEMO

Si el jurado pregunta de dónde salieron los datos:
- Decir: **"Obtuvimos datos de dominios públicos de GitHub, reviews de cursos y comunidades de Discord públicas, todos con licencia de uso académico"**
- NO decir: "los scrapeamos" (a menos que sea 100% cierto y permitido)
- Mostrar la documentación de licencias en el README

---

## 📋 TABLA COMPARATIVA FINAL

| Fuente | Dificultad | Legalidad | Relevancia | Idioma | Tiempo | Veredicto |
|--------|-----------|-----------|------------|--------|--------|-----------|
| HF Discord Dialogues | ★☆☆☆☆ | ✅ | ⭐⭐⭐ | EN | 10 min | ✅ Usar |
| HF GitHub Issues | ★☆☆☆☆ | ✅ | ⭐⭐⭐⭐ | EN | 10 min | ✅ Usar |
| Kaggle Reddit Sentiment | ★☆☆☆☆ | ✅ | ⭐⭐⭐ | EN | 15 min | ✅ Usar |
| Kaggle Coursera Reviews | ★☆☆☆☆ | ✅ | ⭐⭐⭐⭐⭐ | EN/es | 20 min | ✅ Usar |
| Kaggle Stack Overflow | ★☆☆☆☆ | ✅ | ⭐⭐⭐⭐ | EN | 15 min | ✅ Usar |
| Reddit API (PRAW) | ★★☆☆☆ | ✅* | ⭐⭐⭐⭐ | EN | 2-4 h | ⚠️ Alternativa |
| Scraping Discord | ★★☆☆☆ | ❌ | ⭐⭐⭐⭐⭐ | Cualquier | 3-6 h | ❌ NO |
| Scraping Coursera | ★★★★☆ | ❌ | ⭐⭐⭐⭐ | Cualquier | 4-8 h | ❌ NO |
| Propia comunidad ONE | ★☆☆☆☆ | ✅✅ | ⭐⭐⭐⭐⭐ | PT | Variable | 💎 IDEAL |

> ⚠️ Si el jurado valora datos en PORTUGUÉS (por ser programa ONE de Oracle/Alura Brasil), la **propia comunidad del equipo** es la única fuente garantizada. Los datasets públicos listados son principalmente en inglés — pueden argumentar que el sistema es agnóstico al idioma (lang-agnostic).

---

*Documento creado para equipo CommunityLab — Oracle ONE Hackathon G10*