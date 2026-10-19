"""Guard tests for the committed Streamlit configuration.

Streamlit Community Cloud starts the app and health-checks it on port 8501
(``GET http://localhost:8501/healthz``). ``.streamlit/config.toml`` is read by
every ``streamlit run`` over this repository, so pinning ``server.port`` there
also pins it in the cloud: the server listens on another port, the health check
never connects, and the deploy ends in "Error running app" even though the app
itself works.

The fixed local port belongs to the command line (see ``make run``), where it
only affects a local launch.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / ".streamlit" / "config.toml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


def _load_config() -> dict:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_config_file_is_readable_toml():
    assert CONFIG_PATH.is_file()
    assert isinstance(_load_config(), dict)


def test_config_does_not_pin_the_server_port():
    """A pinned port breaks the Community Cloud health check on port 8501."""
    server = _load_config().get("server", {})

    assert "port" not in server, (
        ".streamlit/config.toml no debe fijar server.port: Community Cloud "
        "verifica la salud de la app en el puerto 8501 y el deploy falla con "
        "'Error running app'. Pasá el puerto por línea de comandos (make run)."
    )


def test_makefile_passes_the_local_port_on_the_command_line():
    """The local fixed port must still reach Streamlit, now via the CLI."""
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "--server.port" in makefile
