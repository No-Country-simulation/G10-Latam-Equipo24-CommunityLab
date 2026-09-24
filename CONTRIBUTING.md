# 🔧 CommunityLab — Reglamento del Repositorio

> **Este archivo es la guía de trabajo para todo el equipo. Léelo ANTES de hacer tu primer commit.**

---

## 📁 Estructura del repositorio

```
communitylab/
├── src/
│   ├── ingest/              ← Lógica de ingesta de datos (JSON, CSV, webhooks)
│   ├── analysis/            ← Análisis de sentimiento, categorización, relevancia
│   ├── prompts/             ← System prompts para cada canal (LinkedIn, X, FAQ)
│   ├── orchestration/       ← Pipeline de orquestación (n8n workflows / LangGraph)
│   ├── generators/          ← Generadores de activos por canal
│   ├── oci/                 ← Integración con OCI Object Storage
│   └── interface/           ← Streamlit / Gradio
├── tests/                   ← Tests por módulo
├── data/                    ← Datasets simulados (NO commitear archivos > 5MB)
├── docs/                    ← Documentación, diagramas, decisiones técnicas
├── n8n/                     ← Workflows exportados de n8n (si aplica)
├── notebooks/               ← Jupyter notebooks exploratorios
├── .gitignore
├── requirements.txt
├── README.md
└── CONTRIBUTING.md          ← Este archivo
```

---

## 🌿 Estrategia de Ramas (Branching)

### Regla principal
```
NUNCA se trabaja directamente en main
```

### Naming de ramas
| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Feature | `feat/<descripcion>` | `feat/sentiment-analysis` |
| Bugfix | `fix/<descripcion>` | `fix/oci-upload-error` |
| Documentación | `docs/<descripcion>` | `docs/architecture-diagram` |
| Experimento | `exp/<descripcion>` | `exp/gemini-vs-chatgpt` |

### Flujo
```
1. Crear branch desde main
   $ git checkout main && git pull
   $ git checkout -b feat/mi-tarea

2. Hacer commits con mensajes descriptivos (ver abajo)

3. Cuando termines tu tarea:
   $ git push origin feat/mi-tarea

4. Abrir Pull Request (PR) en GitHub
   → Asignar a un CODEOWNER que NO sea el autor del PR.
   → Si el PR lo abre @Rox-0864, lo aprueba @emanuelperacchia.
   → Si el PR lo abre @emanuelperacchia, lo aprueba @Rox-0864.
   → Si es cambio arquitectónico, pedir también revisión al Tech Lead.

5. Esperar aprobación de un CODEOWNER distinto al autor → merge a main
```

---

## 📝 Convención de Commits

Usamos **Conventional Commits** — esto genera un historial legible y ordenado.

### Formato
```
<tipo>(<scope>): <descripción corta>

[opcional: cuerpo del commit]

[opcional: footer con referencias]
```

### Tipos permitidos
| Tipo | Cuándo usar | Ejemplo |
|------|-------------|---------|
| `feat` | Nueva funcionalidad | `feat(analysis): add sentiment scoring` |
| `fix` | Corrección de bug | `fix(oci): handle empty bucket error` |
| `docs` | Documentación | `docs(readme): add architecture diagram` |
| `refactor` | Reestructurar sin cambiar comportamiento | `refactor(prompts): consolidate templates` |
| `test` | Agregar o modificar tests | `test(sentiment): add edge case for empty input` |
| `chore` | Config, dependencias, CI | `chore: add requirements.txt` |
| `style` | Formato, indentación, espacios | `style(ingest): fix indentation` |

### Scopes del proyecto
- `ingest` — módulo de ingesta
- `analysis` — análisis de sentimiento/temas
- `prompts` — plantillas de prompts
- `orchestration` — pipeline de orquestación
- `generators` — generadores de activos
- `oci` — integración con OCI Object Storage
- `interface` — Streamlit/Gradio
- `data` — datasets
- `docs` — documentación

### Ejemplos reales
```bash
git commit -m "feat(analysis): implement sentiment classification with Gemini"
git commit -m "fix(oci): retry upload on timeout"
git commit -m "docs(architecture): add pipeline flow diagram in mermaid"
git commit -m "refactor(prompts): extract templates to separate module"
git commit -m "test(generators): add unit tests for LinkedIn copy generator"
```

### ❌ Commits que NO aceptamos
```bash
git commit -m "arreglé cosas"
git commit -m "update"
git commit -m "funciona"
git commit -m "prueba"
git commit -m "wip"
```

---

## 🔍 Reglas de Pull Request (PR)

### Antes de abrir un PR
- [ ] Tu código corre sin errores
- [ ] No dejaste print/puts de debug innecesarios
- [ ] Agregaste tests si es funcionalidad nueva
- [ ] Tu branch está actualizado con main (`git rebase main`)

### Formato del PR en GitHub
```markdown
## Qué hice
[Descripción breve de los cambios]

## Por qué
[Contexto: qué problema resuelve o qué feature agrega]

## Cómo probarlo
[Pasos para reproducir / testear]

## Screenshots (si aplica)
[Si hay cambios visuales en la interfaz]

## Checklist
- [ ] Código funciona localmente
- [ ] No rompe funcionalidades existentes
- [ ] Tests pasan
```

### Reglas de review

GitHub **no permite que el autor apruebe su propio PR**. Por eso `CODEOWNERS` tiene 2 personas por carpeta: si el autor es uno de los CODEOWNERS, el otro debe aprobar.

| Quién review | Qué revisa |
|--------------|------------|
| **@Rox-0864** | Código fuente, tests, arquitectura técnica |
| **@emanuelperacchia** | GitHub, docs, configuración y alternate para código/tests |
| **Tech Lead** | Que se alinee con la arquitectura, calidad y límites de cada persona |
| **Par del mismo área** | Que el código sea legible y siga convenciones |

### Merge
- Mínimo **1 aprobación de un CODEOWNER que no sea el autor** para merge.
- Si el PR lo abre `@Rox-0864`, lo aprueba `@emanuelperacchia`.
- Si el PR lo abre `@emanuelperacchia`, lo aprueba `@Rox-0864`.
- Si es cambio grande → **2 aprobaciones**.
- El Tech Lead tiene **veto** en decisiones arquitectónicas.
- **Nunca** hacer force push a main

---

## 🚫 Lo que NO hacemos (nunca, jamás, en ningún universo)

| Regla | Por qué |
|-------|---------|
| No commitear `API keys`, `tokens` o `credentials` | Si se filtra, nos sacan del hackathon. Usar `.env` y `.gitignore` |
| No commitear archivos grandes (> 5MB) | El repo se vuelve inmanejable. Usar `.gitignore` |
| No hacer `git push --force` a main | Puedes borrar el trabajo de todo el equipo |
| No mergeear sin PR | Todo código pasa por review, sin excepciones |
| No commitear `node_modules/`, `__pycache__/`, `.env` | Ya está en `.gitignore`, pero verifiquen |

---

## 📋 Daily Git Ritual (2 minutos al día)

```bash
# 1. Actualizar tu branch con los cambios de main
git checkout main
git pull
git checkout feat/mi-tarea
git rebase main

# 2. Resolver conflictos si los hay (el BE ayuda)

# 3. Push de tus cambios
git push origin feat/mi-tarea

# 4. Si terminaste → abrir PR
```

---

## 🏷️ Releases / Tags (cuando hagamos demo)

El Backend Developer creará tags para marcar versiones clave:
```bash
git tag -a v0.1.0 -m "MVP: ingesta + sentimiento + 1 generador"
git tag -a v0.5.0 -m "Beta: interfaz + OCI + orquestación completa"
git tag -a v1.0.0 -m "Release: demo listo para presentar"
```

---

## 🆘 Si algo se rompe

1. **No hagas force push**
2. Hablá en el canal de comunicación del equipo
3. El Backend Developer te ayuda a resolver el conflicto
4. Si es urgente → el Tech Lead decide la acción correctiva

---

## 📌 Resumen rápido (pegar en el Discord/Slack del equipo)

```
📋 REGLAS GIT — CommunityLab

✅ SIEMPRE crear branch antes de trabajar
✅ Commits con formato: tipo(scope): descripción
✅ Abrir PR antes de merge
✅ Mínimo 1 review de CODEOWNER que no sea autor antes de merge
✅ Actualizar tu branch con main diariamente

❌ NUNCA tocar main directamente
❌ NUNCA commitear API keys
❌ NUNCA force push a main
❌ NUNCA mergeear sin PR
❌ NUNCA commitear "arreglé cosas"
```

---

*Última actualización: Día 1 del hackathon*
*Responsable del repo: Backend Developer*
*Revisor de calidad: Tech Lead*
