"""Common LLM provider client for CommunityLab.

Convention (declared in the README):
    - Every module (analysis, generators, decisions) talks to the LLM ONLY
      through this interface. NEVER import google.generativeai, openai, etc.
      outside this file.
    - The backend is selected via the COMMUNITYLAB_LLM_BACKEND env var:
        "gemini"      -> GeminiClient
        "openai"      -> OpenAIClient
        "ollama"      -> OllamaClient
        "rule_based"  -> RuleBasedClient (deterministic, no API key; demo/tests/CI)

Typical usage from a generator:

    from src.utils.llm import get_llm_client
    client = get_llm_client()
    text = client.generate(prompt_linkedin, temperature=0.7)
    result = parse(text)  # -> validate against the contract Pydantic model

The client returns RAW text. Parsing/validating against the contract is the
caller's responsibility: that keeps the client domain-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

import json
import os


class LLMError(Exception):
    """Base error for LLM provider failures (timeout, rate limit, invalid key)."""


class LLMClient(ABC):
    """Single interface for any LLM provider."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Returns the model's response as raw text (usually JSON).

        `kwargs` accepts common options like `temperature`; each provider maps
        them to its own API (see comments in each client).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Deterministic backend (demo / tests / CI, no API key)
# ---------------------------------------------------------------------------

class RuleBasedClient(LLMClient):
    """Deterministic backend that simulates the LLM with simple rules.

    It never calls an API and always returns the same result for the same
    prompt, which makes it ideal for tests and CI. The result is NOT a real
    analysis: it is a placeholder so the pipeline can run end-to-end without
    credentials. When real rules are implemented, this method returns the
    correct simulated result.
    """

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return json.dumps(
            {
                "simulado": True,
                "nota": "rule_based response (no real LLM)",
            },
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Google Gemini (primary)
# ---------------------------------------------------------------------------

class GeminiClient(LLMClient):
    """Google Gemini client. Reads GEMINI_API_KEY from the environment."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "google-generativeai is not installed. Run: pip install google-generativeai"
            ) from exc

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("Missing GEMINI_API_KEY environment variable.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.model)
        try:
            # NOTE: in Gemini, `temperature` is passed via generation_config,
            # not as a bare kwarg. The final implementer adjusts this.
            response = model.generate_content(prompt, **kwargs)
            return response.text
        except Exception as exc:
            raise LLMError(f"Gemini failed: {exc}") from exc


# ---------------------------------------------------------------------------
# OpenAI (fallback)
# ---------------------------------------------------------------------------

class OpenAIClient(LLMClient):
    """OpenAI client (fallback). Reads OPENAI_API_KEY from the environment."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("Missing OPENAI_API_KEY environment variable.")

        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"OpenAI failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Ollama (local, no API key)
# ---------------------------------------------------------------------------

class OllamaClient(LLMClient):
    """Ollama client (local models). No API key or internet needed.

    Requires Ollama running on localhost. Recommended models: llama3.1,
    mistral, qwen2.5, gemma2. Use the OLLAMA_MODEL env var to pick the model
    (default: llama3.1).
    """

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            import ollama
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "ollama is not installed. Run: pip install ollama"
            ) from exc

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response["message"]["content"]
        except Exception as exc:
            raise LLMError(
                f"Ollama failed (is `ollama serve` running?): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_BACKENDS = {
    "gemini": GeminiClient,
    "openai": OpenAIClient,
    "ollama": OllamaClient,
    "rule_based": RuleBasedClient,
}


def get_llm_client(backend: Optional[str] = None) -> LLMClient:
    """Returns the active LLM client based on COMMUNITYLAB_LLM_BACKEND.

    If `backend` is not passed, reads the env var; if neither, uses
    "rule_based" (safe, no credentials).
    """
    name = backend or os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    client_cls = _BACKENDS.get(name)
    if client_cls is None:
        raise LLMError(
            f"Unknown LLM backend: {name!r}. Valid options: {sorted(_BACKENDS)}."
        )
    return client_cls()
