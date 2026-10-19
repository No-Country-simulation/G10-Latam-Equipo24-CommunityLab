# CI Pipeline

Pipeline de integración continua definido en `.github/workflows/ci.yml`.

## Diagrama de flujo

```mermaid
flowchart TD
    A["Trigger: push o pull_request<br/>en cualquier rama"] --> B["Job test<br/>runs-on: ubuntu-22.04"]
    B --> C["Checkout del código<br/>actions/checkout@v4"]
    C --> D["Setup Python 3.11<br/>actions/setup-python@v5"]
    D --> E["Instalar dependencias<br/>pip install -r requirements.txt"]
    E --> F["Run tests<br/>pytest tests/ -v"]
    F --> G["Run linting<br/>flake8 src tests scripts<br/>config: .flake8"]
    G --> H{"¿Tests y lint OK?"}
    H -- "éxito" --> I["✅ CI exitoso"]
    H -- "fallo" --> J["❌ CI fallido<br/>corregir y re-push"]
```

## Detalles

| Paso | Herramienta | Configuración |
|---|---|---|
| Trigger | GitHub Actions | `push` y `pull_request` en cualquier rama |
| Runner | ubuntu-22.04 | — |
| Test | pytest | `pytest tests/ -v` |
| Lint | flake8 | `flake8 src tests scripts` — `max-line-length` y `extend-ignore` en [`.flake8`](../.flake8) |

> **Nota:** GitHub renderiza Mermaid automáticamente en cualquier `.md` del repo. Para previsualizar localmente, usar VS Code con la extensión *Markdown Preview Mermaid Support* o [mermaid.live](https://mermaid.live).
