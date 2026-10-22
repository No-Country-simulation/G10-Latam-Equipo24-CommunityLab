"""Export Streamlit Community Cloud secrets into the process environment.

Every runtime setting in this project is read with ``os.getenv`` after an
optional ``load_dotenv()`` call, which works because a local checkout has a
``.env`` file. Streamlit Community Cloud has no ``.env``: the values live in
``.streamlit/secrets.toml`` and are exposed through ``st.secrets``, which
``os.getenv`` cannot see.

Importing this module maps each secret into ``os.environ`` (without
overwriting variables that are already set), so the exact same application
code runs locally and on the cloud with no branching.

The OCI private key travels with the rest of the secrets: it is exported as
``OCI_PRIVATE_KEY`` and the OCI client reads the content directly, so no
temporary file is written anywhere.

Placement matters: import this module *before* ``src.pipeline`` /
``src.oci`` so the mapped variables are in place when those modules run
their own ``load_dotenv()`` calls.

Outside a Streamlit runtime (CLI scripts, tests) the import is a no-op.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def export_secrets_to_environ() -> int:
    """Copy ``st.secrets`` entries into ``os.environ``.

    Returns the number of variables that were exported. Existing environment
    variables always win, and a missing Streamlit runtime or absent
    ``secrets.toml`` simply exports nothing.
    """
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:  # pragma: no cover - defensive: no Streamlit runtime
        return 0

    exported = 0
    try:
        items = list(secrets.items())
    except Exception:  # pragma: no cover - malformed/absent secrets.toml
        return 0

    for key, value in items:
        name = str(key)
        if name in os.environ:
            continue
        os.environ[name] = value if isinstance(value, str) else str(value)
        exported += 1
    return exported


# Streamlit executes the app script on import, so the secrets have to be in
# the environment before any module that reads them is imported. Running the
# export at import time is deliberate.
export_secrets_to_environ()
