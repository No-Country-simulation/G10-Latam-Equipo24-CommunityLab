# 🧑‍🤝‍🧩 Fichas para el nuevo compañero — CommunityLab

> Documento de coordinación para incorporar al 7.º compañero sin modificar, reemplazar ni pisar las tareas ya asignadas en `docs/fichas-historias-usuario.md`.

## 1. Principio de coordinación

El nuevo compañero no recibe una ficha existente para “terminarla por otro”. Su rol será de **QA, integración y evidencia de entrega**, con foco en validar que el trabajo de cada propietario sea usable, documentado y listo para demo.

### Reglas obligatorias

- No trabajar directamente sobre `main`.
- No editar archivos de otra persona sin acuerdo explícito.
- No renombrar ni mover archivos ya asignados.
- No cambiar la arquitectura, los modelos ni las interfaces.
- Si se encuentra un bug en código ajeno:
  1. documentar el caso reproducible;
  2. informar al propietario de la ficha;
  3. abrir un issue o PR separado;
  4. esperar aprobación antes de modificar el archivo.
- Todo cambio debe pasar por PR y revisión.
- GitHub **no permite que el autor apruebe su propio PR**.
  - Si `@Rox-0864` abre un PR, lo aprueba `@emanuelperacchia`.
  - Si `@emanuelperacchia` abre un PR, lo aprueba `@Rox-0864`.
  - Si el autor es otra persona, revisar `CODEOWNERS` y pedir aprobación a un CODEOWNER que no sea el autor.
- Las fichas nuevas se crean como issues independientes; no se reemplazan las IDs existentes.

## 2. Rol propuesto

**Rol:** QA, integración y evidencia de entrega.

El nuevo compañero aporta valor verificando que cada sprint cumpla su contrato, preparando evidencia para el equipo y reduciendo el riesgo de que una integración falle en demo.

### Áreas permitidas

- `docs/` para guías, checklists y evidencia.
- `tests/fixtures/` para datos de prueba aislados.
- `tests/` solo para archivos nuevos de pruebas, nunca para modificar tests ya existentes sin coordinación.
- `data/` solo con datasets pequeños y acordados; no sustituir los datasets de otros propietarios.

### Áreas que no debe tocar por decisión propia

- `src/domain/`
- `src/analysis/`
- `src/decisions/`
- `src/generators/`
- `src/oci/`
- `src/interface/`
- `src/api/`
- `.github/workflows/`
- `requirements.txt`
- `.env*`

## 3. Cronograma propuesto

| Sprint | Ficha nueva | Propósito | Dependencia principal |
|--------|-------------|-----------|----------------------|
| Sprint 1 | `HU-S1-009` | QA y evidencia de fundamentos | Terminar o exponer las fichas S1 existentes |
| Sprint 2 | `HU-S2-009` | Matriz de pruebas de análisis y decisiones | Implementaciones S2 y contratos S1 |
| Sprint 3 | `HU-S3-007` | Prueba end-to-end del pipeline | S2 completo + generadores S3 |
| Sprint 4 | `HU-S4-007` | QA de API, UI y OCI | Fichas S4 implementadas |
| Sprint 5 | `HU-S5-008` | QA final y evidencia de demo | Sprint 5 completo |
| Post-sprint | `HU-PS-001` | Estabilización y bugs críticos | Sprint 5 cerrado |

---

## 4. FICHA HU-S1-009

**Título:** QA y evidencia de aceptación del Sprint 1

**Como:** nuevo compañero del equipo  
**Quiero:** verificar que los fundamentos del proyecto estén listos para que los demás trabajen  
**Para que:** el equipo tenga una base estable y documentación clara antes de avanzar

**Sprint:** 1  
**Epic:** QA / Infraestructura  
**Priority:** 🔴 Alta  
**Story Points:** 3  
**Due:** Nuevo compañero  
**Labels:** `feat`, `epic:qa`, `priority:alta`, `sprint:1`

### Criterios de aceptación

- [ ] Se crea `docs/sprint-1/qa-checklist.md`.
- [ ] Se registran los resultados reales de `pytest tests/ -v`.
- [ ] Se registran los resultados reales de `flake8 src/ --max-line-length=100`.
- [ ] Se verifica que la estructura base exista: `src/`, `tests/`, `data/`, `docs/` y `.github/`.
- [ ] Se verifica que `requirements.txt`, `.env.example` y `.gitignore` estén disponibles.
- [ ] Se documentan bloqueos sin modificar código ajeno.
- [ ] Cada resultado queda asociado al propietario de la ficha correspondiente.

### Descripción técnica

El objetivo es crear una evidencia reproducible del estado del Sprint 1. La ficha no implementa modelos, loaders, CI ni configuración: solo ejecuta las verificaciones ya definidas y documenta el resultado.

**Qué hacer:**

1. Leer las fichas `HU-S1-001` a `HU-S1-008`.
2. Ejecutar los comandos de prueba y linting desde la raíz del repositorio.
3. Crear `docs/sprint-1/qa-checklist.md` con:
   - fecha;
   - rama utilizada;
   - comandos ejecutados;
   - resultado esperado;
   - resultado real;
   - observaciones;
   - propietario responsable de resolver cada bloqueo.
4. No cambiar archivos de código para “hacer pasar” una verificación.
5. Si se detecta un error, abrir una observación con pasos para reproducirlo.

**Dónde hacerlo:**

- `docs/sprint-1/qa-checklist.md`
- opcionalmente `docs/sprint-1/evidence.md`

**No modificar:**

- `src/domain/models.py`
- `src/domain/interfaces.py`
- `src/ingest/input_loader.py`
- `src/ingest/normalizer.py`
- `.github/workflows/ci.yml`
- `requirements.txt`
- `.env.example`
- `.gitignore`

### Dependencias

- `HU-S1-001` y `HU-S1-002`: modelos e interfaces disponibles.
- `HU-S1-003` y `HU-S1-004`: loaders y normalizador disponibles.
- `HU-S1-005`: workflow de CI disponible.
- `HU-S1-006`: dependencias y configuración base disponibles.
- `HU-S1-007`: estructura base creada.
- `HU-S1-008`: documentación inicial disponible.

### Colaboración

- **Rox-0864:** revisar criterios de aceptación de modelos e interfaces.
- **Elias:** validar que la evidencia de ingestión sea útil para sus pruebas.
- **emanuelperacchia:** revisar el formato de evidencia de CI.
- **Yis-ai-eng:** confirmar que la guía de setup sea comprensible.
- **Marcelo Rolon:** confirmar que la estructura base permita trabajar en UI.
- **Antonio3051:** coordinar el documento para no duplicar la documentación técnica.

---

## 5. FICHA HU-S2-009

**Título:** Matriz de pruebas para análisis y decisiones

**Como:** nuevo compañero del equipo  
**Quiero:** definir casos de prueba claros para los módulos de análisis y decisiones  
**Para que:** Rox, Elias e Yis puedan validar sus implementaciones sin rediseñar las pruebas en cada sprint

**Sprint:** 2  
**Epic:** QA / Análisis / Decisiones  
**Priority:** 🟡 Media  
**Story Points:** 5  
**Due:** Nuevo compañero  
**Labels:** `feat`, `epic:qa`, `priority:media`, `sprint:2`

### Criterios de aceptación

- [ ] Se crea `docs/pruebas/analisis-decisiones.md`.
- [ ] Se documentan casos positivos, negativos y neutrales para sentimiento.
- [ ] Se documentan las seis categorías esperadas:
  - `duda_tecnica`
  - `testimonio`
  - `feedback`
  - `pregunta_general`
  - `discusion`
  - `otro`
- [ ] Se documentan casos de relevancia alta y baja.
- [ ] Se documentan las reglas del motor de decisiones.
- [ ] Se documentan escenarios para el detector de miembros en riesgo.
- [ ] Se documentan escenarios para el detector de dudas recurrentes.
- [ ] Se añade un fixture aislado si es necesario: `tests/fixtures/analysis-decisiones.json`.
- [ ] No se modifica código existente de análisis, decisiones o prompts.

### Descripción técnica

La ficha crea una matriz de comportamiento, no una implementación. Cada caso debe indicar entrada, resultado esperado, propietario del módulo y prueba asociada.

**Qué hacer:**

1. Leer `HU-S2-001` a `HU-S2-007`.
2. Crear una tabla por módulo:
   - entrada;
   - comportamiento esperado;
   - resultado esperado;
   - caso de error;
   - archivo de prueba.
3. Incluir ejemplos breves en español.
4. Separar los casos de cada propietario para evitar solapamientos.
5. Crear un fixture JSON solo si ayuda a reproducir un caso y no duplica datos de otro archivo.

**Dónde hacerlo:**

- `docs/pruebas/analisis-decisiones.md`
- `tests/fixtures/analysis-decisiones.json` si se justifica

**No modificar:**

- `src/analysis/sentiment.py`
- `src/analysis/categorization.py`
- `src/analysis/relevance.py`
- `src/analysis/orchestrator.py`
- `src/decisions/engine.py`
- `src/decisions/member_risk.py`
- `src/decisions/recurring_topics.py`
- `src/prompts/templates.py`

### Dependencias

- `HU-S1-001` y `HU-S1-002` deben estar disponibles para conocer los modelos e interfaces.
- `HU-S2-001` a `HU-S2-005` deben estar implementadas antes de validar resultados concretos.
- `HU-S2-006` y `HU-S2-007` deben tener sus criterios de negocio definidos.
- `HU-S2-008` debe definir el comportamiento de prompts y configuración.

### Colaboración

- **Rox-0864:** propietario de análisis, orquestación y motor de decisiones.
- **Elias:** propietario del detector de miembros en riesgo.
- **Yis-ai-eng:** propietario del detector de dudas recurrentes.
- **emanuelperacchia:** propietario de prompts y configuración.
- El nuevo compañero solo documenta y prepara casos; no implementa los analizadores.

---

## 6. FICHA HU-S3-007

**Título:** Prueba end-to-end del pipeline y contrato JSON

**Como:** nuevo compañero del equipo  
**Quiero:** validar que un batch completo entre, se procese y produzca una salida coherente  
**Para que:** el equipo pueda demostrar el flujo completo sin depender de revisiones manuales aisladas

**Sprint:** 3  
**Epic:** QA / Infraestructura  
**Priority:** 🔴 Alta  
**Story Points:** 5  
**Due:** Nuevo compañero  
**Labels:** `feat`, `epic:qa`, `priority:alta`, `sprint:3`

### Criterios de aceptación

- [ ] Se crea `docs/pruebas/pipeline-e2e.md`.
- [ ] Se usa un batch de prueba con, como mínimo, 10 mensajes.
- [ ] Se verifica el flujo:
  `JSON de entrada → ingestión → análisis → decisiones → generadores → JSON de salida`.
- [ ] Se comprueba que el JSON de salida conserva `batch_id`, `analysis`, `decisions`, `assets`, `summary` y `alerts`.
- [ ] Se documenta el resultado de una entrada válida.
- [ ] Se documenta el resultado de una entrada inválida.
- [ ] Se registran errores y se asignan a su propietario.
- [ ] No se modifica el pipeline de `src/pipeline.py` ni los generadores existentes.

### Descripción técnica

La ficha valida el contrato completo del sistema. Debe servir como guía de ejecución local y como evidencia para el Sprint 5.

**Qué hacer:**

1. Leer `HU-S2-001` a `HU-S2-008`.
2. Leer `HU-S3-001` a `HU-S3-006`.
3. Preparar un batch de 10 mensajes en un fixture nuevo o en un archivo de prueba acordado.
4. Ejecutar el pipeline con backend demo o mock cuando no haya credenciales externas.
5. Comparar la salida con el JSON esperado.
6. Documentar:
   - comando ejecutado;
   - entrada usada;
   - salida observada;
   - diferencias;
   - siguiente responsable.
7. No corregir código ajeno para que la prueba pase.

**Dónde hacerlo:**

- `docs/pruebas/pipeline-e2e.md`
- `tests/fixtures/e2e/` si se requiere un fixture separado

**No modificar:**

- `src/pipeline.py`
- `src/ingest/input_loader.py`
- `src/ingest/normalizer.py`
- `src/analysis/*`
- `src/decisions/*`
- `src/generators/*`

### Dependencias

- `HU-S2-001` a `HU-S2-008` deben estar completas.
- `HU-S3-001` a `HU-S3-004` deben estar completas.
- `HU-S3-005` debe estar implementada.
- `HU-S3-006` debe existir o estar coordinada con Elias.

### Colaboración

- **Rox-0864:** propietario del pipeline y los analizadores.
- **Yis-ai-eng:** propietario de los generadores.
- **Elias:** propietario de la validación de entrada.
- **emanuelperacchia:** propietario de configuración y prompts.
- El nuevo compañero ejecuta y documenta; los dueños corrigen sus módulos.

---

## 7. FICHA HU-S4-007

**Título:** QA de API, UI y OCI

**Como:** nuevo compañero del equipo  
**Quiero:** validar las capas visibles del sistema y la integración con OCI  
**Para que:** el community manager pueda usar la aplicación y el equipo tenga evidencia de que la integración funciona

**Sprint:** 4  
**Epic:** QA / UI / OCI  
**Priority:** 🟡 Media  
**Story Points:** 5  
**Due:** Nuevo compañero  
**Labels:** `feat`, `epic:qa`, `priority:media`, `sprint:4`

### Criterios de aceptación

- [ ] Se crea `docs/pruebas/ui-api-oci.md`.
- [ ] Se verifica `GET /health`.
- [ ] Se verifica `POST /procesar` con un JSON válido.
- [ ] Se verifica `POST /procesar` con un JSON inválido.
- [ ] Se revisa el dashboard en `localhost:8501`.
- [ ] Se revisa el panel de curaduría.
- [ ] Se revisa el panel de alertas.
- [ ] Se documenta el flujo de aprobación, edición y rechazo.
- [ ] Se documenta una prueba local de OCI o se marca claramente como pendiente de credenciales.
- [ ] No se modifica código de Streamlit, API u OCI sin aprobación.

### Descripción técnica

La ficha cubre la experiencia del usuario y la integración externa. Debe distinguir entre prueba local, prueba con datos mock y prueba real con OCI.

**Qué hacer:**

1. Leer `HU-S4-001` a `HU-S4-006`.
2. Levantar la API y Streamlit localmente.
3. Ejecutar las pruebas manuales descritas.
4. Capturar evidencia textual o screenshots en `docs/pruebas/ui-api-oci.md`.
5. Registrar credenciales y URLs, pero nunca guardar claves en el repositorio.
6. Si falta OCI, documentar el bloqueo con los datos exactos necesarios.

**Dónde hacerlo:**

- `docs/pruebas/ui-api-oci.md`
- `docs/pruebas/screenshots/` si se permiten capturas

**No modificar:**

- `src/interface/app.py`
- `src/interface/pages/*`
- `src/api/app.py`
- `src/oci/client.py`
- `src/oci/storage.py`

### Dependencias

- `HU-S4-001` y `HU-S4-002`: cliente y storage OCI.
- `HU-S4-003` a `HU-S4-005`: dashboard, curaduría y alertas.
- `HU-S4-006`: API y health check.
- `HU-S3-005`: pipeline funcional.
- `HU-S2-006` y `HU-S2-007`: datos de alertas y dudas recurrentes.

### Colaboración

- **emanuelperacchia:** OCI, credenciales y despliegue.
- **Marcelo Rolon:** Streamlit, dashboard, curaduría y alertas.
- **Rox-0864:** API y contrato de procesamiento.
- **Elias:** datos de prueba para OCI.
- El nuevo compañero no cambia la interfaz ni la lógica de storage.

---

## 8. FICHA HU-S5-008

**Título:** QA final y evidencia para la demo

**Como:** nuevo compañero del equipo  
**Quiero:** comprobar que el proyecto completo funciona antes de la presentación  
**Para que:** el jurado vea un flujo estable y el equipo tenga una lista clara de pendientes

**Sprint:** 5  
**Epic:** QA / Demo  
**Priority:** 🔴 Alta  
**Story Points:** 5  
**Due:** Nuevo compañero  
**Labels:** `fix`, `epic:qa`, `priority:alta`, `sprint:5`

### Criterios de aceptación

- [ ] Se crea `docs/demo/qa-final.md`.
- [ ] Se ejecuta `pytest tests/ -v`.
- [ ] Se ejecuta `flake8 src/ --max-line-length=100`.
- [ ] Se procesa el dataset de prueba completo.
- [ ] Se verifica el pipeline end-to-end.
- [ ] Se verifica la API `/procesar` y `/health`.
- [ ] Se verifica el dashboard y los paneles de Streamlit.
- [ ] Se verifica OCI upload/download si las credenciales están disponibles.
- [ ] Se documenta el video y la presentación con enlaces o ubicación.
- [ ] Se separan errores críticos, menores y pendientes de demo.

### Descripción técnica

Esta ficha es la última línea de defensa antes de la demo. No busca añadir funcionalidades nuevas, sino comprobar que lo existente cumple el contrato y dejar evidencia reproducible.

**Qué hacer:**

1. Leer `HU-S5-001` a `HU-S5-007`.
2. Ejecutar pruebas automáticas.
3. Ejecutar la demo local completa.
4. Comparar resultados contra el JSON esperado.
5. Registrar errores con prioridad y propietario.
6. Preparar una versión limpia de la evidencia para el equipo.
7. No hacer cambios correctivos fuera del PR acordado.

**Dónde hacerlo:**

- `docs/demo/qa-final.md`
- `docs/demo/evidence/` si se requiere evidencia adicional

**No modificar:**

- código fuente;
- configuración de producción;
- credenciales;
- dataset de otro propietario.

### Dependencias

- Sprint 1, 2, 3 y 4 completados o marcados como bloqueados.
- `HU-S5-001` a `HU-S5-007` disponibles.
- Dataset completo de `HU-S5-005`.
- Documentación de despliegue de `HU-S5-002`.
- Video y presentación de `HU-S5-003` y `HU-S5-004`.

### Colaboración

- **Rox-0864:** QA técnico y corrección de bugs.
- **emanuelperacchia:** despliegue y OCI.
- **Marcelo Rolon:** UI y demo visual.
- **Yis-ai-eng:** generadores y presentación.
- **Elias:** dataset e ingestión.
- **Antonio3051:** documentación y video.

---

## 9. HU-PS-001 — Post-sprint

**Título:** Estabilización y bugs críticos posteriores a la demo

**Como:** nuevo compañero del equipo  
**Quiero:** mantener el proyecto estable después de la entrega inicial  
**Para que:** los cambios posteriores no introduzcan regresiones

**Sprint:** Post-sprint  
**Epic:** QA / Mantenimiento  
**Priority:** 🟡 Media  
**Story Points:** 3  
**Due:** Nuevo compañero  
**Labels:** `fix`, `epic:qa`, `priority:media`, `post-sprint`

### Criterios de aceptación

- [ ] Se crea `docs/post-sprint/hardening-checklist.md`.
- [ ] Se documentan los bugs reportados después de la demo.
- [ ] Cada bug recibe prioridad, reproducible, impacto y propietario.
- [ ] Se ejecuta la suite completa antes y después de cualquier corrección.
- [ ] Se documentan decisiones de workaround.
- [ ] No se aceptan correcciones sin PR ni revisión.

### Descripción técnica

La tarea posterior a sprint convierte los problemas reales de uso en trabajo ordenado. La prioridad es evitar cambios impulsivos y proteger el trabajo de los propietarios.

**Qué hacer:**

1. Recopilar reportes.
2. Clasificar por criticidad.
3. Crear un issue o PR por cambio.
4. Coordinar con el propietario del módulo.
5. Actualizar la checklist de estabilización.

**Dónde hacerlo:**

- `docs/post-sprint/hardening-checklist.md`
- issues o PRs individuales para bugs reales

**No modificar:**

- código ajeno sin autorización;
- archivos de configuración;
- credenciales;
- documentación de arquitectura sin coordinación.

### Dependencias

- Sprint 5 cerrado.
- Bugs o feedback real de la demo.
- PRs y revisiones ya abiertas.

---

## 10. Matriz de colaboración por sprint

| Sprint | Propietarios existentes | Aporte del nuevo compañero | Límite de colaboración |
|--------|-------------------------|----------------------------|------------------------|
| S1 | Rox, Elias, Emanuel, Yis, Marcelo, Antonio | QA, checklist y evidencia | No tocar sus archivos |
| S2 | Rox, Elias, Yis, Emanuel | Matriz de pruebas y fixtures | No implementar analizadores ni reglas |
| S3 | Yis, Rox, Elias | Evidencia end-to-end | No modificar pipeline ni generadores |
| S4 | Marcelo, Emanuel, Rox | QA de API, UI y OCI | No cambiar pantallas ni storage |
| S5 | Todo el equipo | QA final y demo | No corregir código sin PR |
| Post-sprint | Todo el equipo | Triage y estabilización | No hacer fixes silenciosos |

## 11. Protocolo de entrega

1. Crear una rama desde `main`:
   ```bash
   git checkout main
   git pull
   git checkout -b docs/nuevo-compañero-sprint-1
   ```
2. Trabajar solo en los archivos indicados por la ficha.
3. Ejecutar:
   ```bash
   pytest tests/ -v
   flake8 src/ --max-line-length=100
   git diff --check
   ```
4. Abrir PR con:
   - qué se hizo;
   - qué fichas se verificaron;
   - comandos ejecutados;
   - resultados;
   - bloqueos;
   - propietarios a los que se notificó.
5. Solicitar revisión a un CODEOWNER que no sea el autor:
   - si el autor es `@Rox-0864`, pedir aprobación a `@emanuelperacchia`;
   - si el autor es `@emanuelperacchia`, pedir aprobación a `@Rox-0864`;
   - si el autor es otra persona, revisar `CODEOWNERS` y pedir revisión al propietario del epic.
6. No mergear directamente a `main`.

## 12. Resumen para GitHub Project

Las fichas propuestas son independientes de las 35 fichas principales y de los auxiliares existentes. Se recomienda crearlas como issues adicionales con el mismo formato de labels, sprint y milestone.

**No se debe:**

- cambiar el owner de una ficha existente;
- eliminar una ficha existente;
- renombrar una ficha existente;
- fusionar dos fichas para ocultar dependencias;
- asignar automáticamente una tarea de código a otra persona.

**Sí se debe:**

- usar estas fichas como soporte de QA e integración;
- enlazar cada nueva ficha con las fichas que valida;
- documentar dependencias antes de empezar;
- pedir revisión antes de modificar cualquier archivo ajeno;
- no pedir aprobación al propio autor del PR.

---

*Documento preparado para CommunityLab — 7.º compañero — Sprint 1 en curso.*
