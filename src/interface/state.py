"""Shared persistence layer for the dashboard's operational state.

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

import hashlib
import json
import os
import re
import sys
from datetime import date
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

# Directory holding the per-period curation mirrors.
CURATION_STATE_DIR = Path(
    os.environ.get(
        "COMMUNITYLAB_CURATION_DIR",
        str(REPO_ROOT / "storage" / "estado"),
    )
)

# OCI object key of the global attended-state dict.
ATTENDED_OCI_KEY = "estado/derivados-atendidos.json"

# Asset kinds whose curation decision is persisted per period.
CURATION_CHANNELS = ("linkedin", "newsletter", "faq")

# Period labels come from user-supplied envelopes: keep them safe as filenames.
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


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


def _oci_get_dict(key: str) -> dict:
    """Read a JSON object from OCI. Never raises; ``{}`` when unavailable."""
    try:
        value = OCIStorageClient().get_json(DEFAULT_BUCKET, key, None)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _oci_put_dict(key: str, data: dict) -> bool:
    """Write a JSON object to OCI. Never raises; False when unavailable."""
    try:
        return bool(OCIStorageClient().put_json(DEFAULT_BUCKET, key, data))
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


# ---------------------------------------------------------------------------
# Domain C — per-period curation decisions
# ---------------------------------------------------------------------------


def _candidate_key(autor, texto_original) -> str:
    """Stable identity of a candidate: hash of ``autor`` + ``texto_original``.

    The identity must survive a reload, when the same candidate shows up
    under a different widget index. The newline separator keeps two different
    pairs from producing the same seed.
    """
    seed = f"{autor or ''}\n{texto_original or ''}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def _faq_key(tema) -> str:
    """Stable identity of a FAQ theme (a theme has no single author)."""
    return hashlib.sha1(str(tema or "").encode("utf-8")).hexdigest()[:12]


def _CURATION_OCI_KEY(periodo) -> str:
    """OCI object key holding the curation decisions of one period."""
    return f"estado/curacion-{periodo}.json"


def _curation_path(periodo) -> Path:
    """Local mirror path of the curation decisions of one period."""
    slug = _UNSAFE_NAME_RE.sub("_", str(periodo)).strip("_") or "periodo"
    return CURATION_STATE_DIR / f"curacion-{slug}.json"


def load_curation(session_state, periodo) -> dict:
    """Load the curation decisions of one period: OCI first, local wins.

    Returns one dict per channel (``linkedin``, ``newsletter``, ``faq``)
    mapping a candidate key to its status. The result is cached in
    ``session_state`` so the dashboard does not re-read the stores on every
    re-render.
    """
    empty = {canal: {} for canal in CURATION_CHANNELS}
    if not periodo:
        return empty

    cache_key = f"curacion_{periodo}"
    cached = session_state.get(cache_key) if session_state is not None else None
    if isinstance(cached, dict):
        return cached

    local = _read_json_dict(_curation_path(periodo))
    remote = _oci_get_dict(_CURATION_OCI_KEY(periodo))

    # The merge is per channel AND per candidate: a whole-channel overwrite
    # would silently drop the decisions the other store still holds. The
    # local mirror wins, because it only diverged while OCI was unreachable.
    result = {canal: {} for canal in CURATION_CHANNELS}
    for canal in CURATION_CHANNELS:
        remote_entries = remote.get(canal)
        local_entries = local.get(canal)
        result[canal] = {
            **(remote_entries if isinstance(remote_entries, dict) else {}),
            **(local_entries if isinstance(local_entries, dict) else {}),
        }

    # Heal the divergence: the merged state goes back to OCI, so the next
    # reader sees the same decisions from both stores.
    if remote and any(
        result[canal] != (remote.get(canal) or {}) for canal in CURATION_CHANNELS
    ):
        _oci_put_dict(_CURATION_OCI_KEY(periodo), result)

    if session_state is not None:
        session_state[cache_key] = result
    return result


def set_curation(session_state, periodo, canal, key, estado) -> None:
    """Persist one curation decision for a period."""
    if not periodo or canal not in CURATION_CHANNELS:
        return

    data = load_curation(session_state, periodo)
    data.setdefault(canal, {})[key] = estado
    _write_json_dict(_curation_path(periodo), data)
    _oci_put_dict(_CURATION_OCI_KEY(periodo), data)


def _current_periodo() -> str:
    """Current ISO week as ``<year>-semana-<week>`` (matches the OCI folders)."""
    iso = date.today().isocalendar()
    return f"{iso[0]}-semana-{iso[1]:02d}"


def _extract_periodo(session_state, results) -> str:
    """Resolve the period of a batch.

    Order: the period already stashed in ``session_state``, then the period
    encoded in the OCI object path (``activos/<periodo>/...``), then the
    current ISO week.
    """
    if session_state is not None:
        periodo = session_state.get("periodo_referencia")
        if periodo:
            return str(periodo)

    storage = (results or {}).get("almacenamiento_oci") or {}
    ruta = storage.get("ruta_objeto") if isinstance(storage, dict) else ""
    match = re.search(r"activos/([^/]+)/", str(ruta or ""))
    if match:
        return match.group(1)

    return _current_periodo()
