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
    prompt, which makes it ideal for tests and CI. The result is contract-shaped
    JSON for supported prompt types, or a safe fallback otherwise.
    """

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not prompt:
            return json.dumps(
                {
                    "simulado": True,
                    "nota": "rule_based response (no real LLM)",
                },
                ensure_ascii=False,
            )

        prompt_lower = prompt.lower()

        # Analysis prompt (unified analyzer)
        if "analizá el mensaje de una comunidad técnica" in prompt_lower:
            text_lower = prompt_lower
            # Question-like content
            question_indicators = (
                "?", "¿", "cómo hago", "cómo se", "ayuda", "error", "bug",
                "no funciona", "problema", "falla", "duda"
            )
            has_question = any(ind in text_lower for ind in question_indicators)

            # Achievement/testimonial-like content
            testimonial_indicators = (
                "logré", "conseguí", "obtuve", "gracias", "feliz", "orgulloso",
                "nuevo trabajo", "promoción", "aprobé", "exito", "éxito"
            )
            has_testimonial = "!" in text_lower or any(
                ind in text_lower for ind in testimonial_indicators
            )

            if has_question and not has_testimonial:
                payload = {
                    "sentiment": {
                        "type": "neutral",
                        "score": 0.5,
                        "reasoning": "Deterministic rule: question detected",
                    },
                    "categorization": {
                        "category": "pregunta_tecnica",
                        "confidence": 0.9,
                        "topics": ["consulta"],
                        "entities": [],
                    },
                    "relevance": {"score": 0.4},
                }
            elif has_testimonial:
                payload = {
                    "sentiment": {
                        "type": "positivo",
                        "score": 0.9,
                        "reasoning": "Deterministic rule: achievement detected",
                    },
                    "categorization": {
                        "category": "testimonio",
                        "confidence": 0.9,
                        "topics": ["logro"],
                        "entities": [],
                    },
                    "relevance": {"score": 0.8},
                }
            else:
                payload = {
                    "sentiment": {
                        "type": "neutral",
                        "score": 0.5,
                        "reasoning": "Deterministic rule: discussion default",
                    },
                    "categorization": {
                        "category": "discusion",
                        "confidence": 0.9,
                        "topics": ["comunidad"],
                        "entities": [],
                    },
                    "relevance": {"score": 0.3},
                }
            # Clamp scores to [0,1]
            payload["sentiment"]["score"] = max(
                0.0, min(1.0, float(payload["sentiment"]["score"]))
            )
            payload["relevance"]["score"] = max(
                0.0, min(1.0, float(payload["relevance"]["score"]))
            )
            return json.dumps(payload, ensure_ascii=False)

        # LinkedIn generator prompt
        if "post de linkedin" in prompt_lower:
            return json.dumps(
                {
                    "titulo": "Logro destacado de la comunidad",
                    "copy": (
                        "Hoy celebramos un logro que refleja el esfuerzo y la "
                        "constancia de nuestra comunidad técnica."
                    ),
                    "canal_recomendado": "LinkedIn Oficial",
                    "potencial_engagement": "Medio",
                },
                ensure_ascii=False,
            )

        # Newsletter generator prompt
        if "destaque de newsletter semanal" in prompt_lower:
            return json.dumps(
                {
                    "seccion": "Logro de la Semana",
                    "titular": "Logro destacado de la semana",
                    "resumen": (
                        "Un integrante de la comunidad alcanzó un hito que "
                        "inspira a seguir construyendo juntos."
                    ),
                },
                ensure_ascii=False,
            )

        # FAQ generator prompt
        if "tema de una faq" in prompt_lower:
            return json.dumps(
                {
                    "tema": "Consulta técnica sobre desarrollo",
                },
                ensure_ascii=False,
            )

        # Unknown prompt - safe fallback
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
    """Ollama client with two modes, selected by the presence of a key.

    - Local mode (default): no API key needed. Talks to a running `ollama
      serve` on localhost through the `ollama` package. Model from
      OLLAMA_MODEL (default: llama3.1).
    - Cloud mode: set OLLAMA_API_KEY. Uses the OpenAI-compatible endpoint
      `https://ollama.com/v1` (override with OLLAMA_BASE_URL) with the
      `openai` SDK — no local server required. The model must be a cloud
      catalog id (see https://ollama.com/api/tags), e.g. `gemma4:31b`.
    """

    CLOUD_BASE_URL = "https://ollama.com/v1"

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.base_url = os.getenv("OLLAMA_BASE_URL", self.CLOUD_BASE_URL)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if self.api_key:
            return self._generate_cloud(prompt, **kwargs)
        return self._generate_local(prompt, **kwargs)

    def _generate_local(self, prompt: str, **kwargs: Any) -> str:
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

    def _generate_cloud(self, prompt: str, **kwargs: Any) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        try:
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise LLMError(f"Ollama Cloud failed: {exc}") from exc


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
