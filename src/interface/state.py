"""Shared persistence layer for the dashboard's attended state.

Why a separate module: the Streamlit app is executed as a *copy* of
``src/interface/app.py`` (both by ``streamlit`` itself and by
``streamlit.testing.v1.AppTest``), so a seam patched on ``src.interface.app``
never reaches the copy that actually runs. This module is imported *by name*,
so every copy of the script shares ONE instance of it — the seams below are
therefore read at call time and always agree.

Policy (design D4): read OCI-first and merge with the local mirror (local
wins, because it only diverged while OCI was unreachable); write through to
the local mirror and then to OCI on a best-effort basis. An OCI failure never
reaches the UI.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.oci.storage import DEFAULT_BUCKET, OCIStorage as OCIStorageClient  # noqa: E402

# ---------------------------------------------------------------------------
# Seams. Read at call time, so patching them on THIS module is enough.
# ---------------------------------------------------------------------------

# Local mirror of the attended-state dict.
ATTENDED_PATH = Path(
    os.environ.get(
        "COMMUNITYLAB_ATTENDED_PATH",
        str(REPO_ROOT / "storage" / "estado" / "derivados-atendidos.json"),
    )
)

# OCI object key of the global attended-state dict.
ATTENDED_OCI_KEY = "estado/derivados-atendidos.json"


# ---------------------------------------------------------------------------
# JSON helpers. None of them raise: a broken store degrades to "no state".
# ---------------------------------------------------------------------------


def _read_json_dict(path) -> dict:
    """Read a JSON object from ``path``; ``{}`` when missing or corrupt."""
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json_dict(path, data: dict) -> bool:
    """Write ``data`` as JSON to ``path``. Returns True when it landed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError):
        return False
    return True


def _bucket() -> str:
    """Target bucket of the state objects, resolved at call time.

    ``OCI_BUCKET_NAME`` is the canonical bucket configuration — the pipeline
    resolves it the same way (``src/pipeline.py``) — and ``DEFAULT_BUCKET`` is
    the fallback when the variable is absent. Both are read at call time so
    the seams stay patchable.
    """
    return os.environ.get("OCI_BUCKET_NAME") or DEFAULT_BUCKET


def _oci_get_dict(key: str) -> dict:
    """Read a JSON object from OCI. Never raises; ``{}`` when unavailable."""
    try:
        value = OCIStorageClient().get_json(_bucket(), key, None)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _oci_put_dict(key: str, data: dict) -> bool:
    """Write a JSON object to OCI. Never raises; False when unavailable."""
    try:
        return bool(OCIStorageClient().put_json(_bucket(), key, data))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Domain B — globally persisted "atendido" state
# ---------------------------------------------------------------------------


def _load_attended() -> dict:
    """Load the attended-state dict: OCI first, local mirror wins.

    The mirror only diverges from OCI when it was edited while OCI was
    unreachable, so the merge keeps the local value and pushes the result
    back to OCI to heal the divergence.
    """
    local = _read_json_dict(ATTENDED_PATH)
    remote = _oci_get_dict(ATTENDED_OCI_KEY)
    if not remote:
        return local

    merged = {**remote, **local}
    if merged != remote:
        _oci_put_dict(ATTENDED_OCI_KEY, merged)
    return merged


def _save_attended(attended: dict) -> None:
    """Persist the attended-state dict locally and, best-effort, to OCI.

    The local mirror is written first: it is the only store guaranteed to be
    reachable, and OCI must never be able to block the dashboard.
    """
    _write_json_dict(ATTENDED_PATH, attended)
    _oci_put_dict(ATTENDED_OCI_KEY, attended)


def _attended_cache(session_state) -> dict:
    """Return the session cache of the attended state, loading it if absent."""
    if session_state is None:
        return _load_attended()

    attended = session_state.get("derivados_atendidos")
    if attended is None:
        attended = _load_attended()
        session_state["derivados_atendidos"] = attended
    return attended


def is_atendido(session_state, message_id) -> bool:
    """Whether a derived message is marked as attended.

    Falls back to the persisted state when the key is not yet in
    ``session_state``, so a reload restores prior attendance decisions.
    """
    return bool(_attended_cache(session_state).get(message_id))


def set_atendido(session_state, message_id, value) -> None:
    """Mark a derived message as attended (or not) and persist it."""
    attended = _attended_cache(session_state)
    attended[message_id] = bool(value)
    _save_attended(attended)
