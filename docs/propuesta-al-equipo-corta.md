# Propuesta al equipo — versión corta

**Rama:** `feat/ingesta-mejoras` (sin pushear, sin PR). **Nada está en `main`.**
**Detalle completo:** `docs/propuesta-al-equipo.md`

## Qué hicimos (fuera del repo)

- **Ingesta multicanal:** CSV + Telegram + webhook HTTP, con merge de varias
  fuentes en una corrida. El JSON del desafío sigue funcionando.
- **Bot de Telegram:** analiza cada mensaje en tiempo real y responde
  sentimiento + temas + decisión. Ya probado en vivo.
- **Línea de tiempo semanal:** 4 semanas sintéticas + runner de evolución
  (dudas 65 % → 21 %, logros 10 % → 57 %, LinkedIn desde la semana 2).
- **Refactor:** el pipeline corre en memoria (`_run_with_batch`); lo reusan el
  webhook y el bot.
- **7 commits, 21 archivos, +2.799 líneas.** Suite: **230 passed, 1 skipped**.

## El pedido: contrato para los gráficos

El dashboard (HU-S4-003) pide torta de sentimiento y top-10 de temas, y hoy el
contrato no alcanza: el pipeline **calcula** esas distribuciones y las
**descarta**. Proponemos **agregar dos campos aditivos** (nada actual cambia):

- `distribucion_sentimiento` → conteo Positivo / Negativo / Neutral.
- `temas_principales_conteo` → top 10 con frecuencia.

## Bot y Streamlit (aclaración)

Son **dos procesos**: el bot no vive dentro de Streamlit. Comparten el código
de ingesta y el destino de los datos. Para la demo: un botón en el dashboard
que trae mensajes nuevos y corre el pipeline.

## Lo que necesitamos decidir

1. ¿Aprobamos el **contrato aditivo**? Es lo único que traba los gráficos.
2. ¿El bot es **scope del S5** o queda como demo?
3. La rama pasa las 400 líneas → proponemos **PRs encadenados**.
4. Cerrar **`#94`** primero; después subir ingesta.
