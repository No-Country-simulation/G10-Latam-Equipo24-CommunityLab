"""Cliente común para proveedores LLM — CommunityLab.

Convención (declarada en el README de la propuesta):

    - Todos los módulos (análisis, generadores, decisiones) hablan con el LLM
      SOLO a través de esta interfaz. NUNCA importes google.generativeai,
      openai, etc. fuera de este archivo.
    - El backend se elige con la variable de entorno COMMUNITYLAB_LLM_BACKEND:
        "gemini"      → GeminiClient
        "openai"      → OpenAIClient
        "rule_based"  → RuleBasedClient (determinista, sin API key; demo/tests/CI)

Uso típico desde un generador:

    from src.utils.llm import get_llm_client

    client = get_llm_client()
    texto = client.generate(prompt_linkedin, temperature=0.7)
    resultado = parsear(texto)  # ← validar contra el modelo Pydantic del contrato

El cliente devuelve TEXTO crudo. Parsear/validar contra el contrato es
responsabilidad de quien llama: así el cliente queda agnóstico del dominio.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

import json
import os


class LLMError(Exception):
    """Error base para fallas del proveedor LLM (timeout, rate limit, key inválida)."""


class LLMClient(ABC):
    """Interfaz única para cualquier proveedor LLM."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Devuelve la respuesta del modelo como texto crudo (normalmente JSON).

        `kwargs` admite opciones comunes como `temperature`, con la salvedad de
        que cada proveedor las mapea a su API (ver comentarios en cada cliente).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Backend determinista (demo / tests / CI, sin API key)
# ---------------------------------------------------------------------------

class RuleBasedClient(LLMClient):
    """Backend determinista que simula al LLM con reglas simples.

    No llama a ninguna API y devuelve siempre el mismo resultado para el mismo
    prompt, lo que lo hace ideal para tests y CI. El resultado NO es un análisis
    real: es un placeholder para que el pipeline corra de punta a punta sin
    credenciales. Cuando se implementen las reglas reales (keyword matching por
    tipo, etc.), este método devolverá el resultado simulado correcto.
    """

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return json.dumps(
            {
                "simulado": True,
                "nota": "respuesta rule_based (sin LLM real)",
            },
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Google Gemini (principal)
# ---------------------------------------------------------------------------

class GeminiClient(LLMClient):
    """Cliente de Google Gemini. Lee GEMINI_API_KEY del entorno."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "google-generativeai no está instalado. Corré: pip install google-generativeai"
            ) from exc

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("Falta la variable de entorno GEMINI_API_KEY.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.model)
        try:
            # NOTA: en Gemini, `temperature` se pasa vía generation_config, no
            # como kwarg suelto. El implementador final ajusta esto.
            response = model.generate_content(prompt, **kwargs)
            return response.text
        except Exception as exc:
            raise LLMError(f"Gemini falló: {exc}") from exc


# ---------------------------------------------------------------------------
# OpenAI (respaldo)
# ---------------------------------------------------------------------------

class OpenAIClient(LLMClient):
    """Cliente de OpenAI (respaldo). Lee OPENAI_API_KEY del entorno."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "openai no está instalado. Corré: pip install openai"
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("Falta la variable de entorno OPENAI_API_KEY.")

        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"OpenAI falló: {exc}") from exc


# ---------------------------------------------------------------------------
# Ollama (local, sin API key)
# ---------------------------------------------------------------------------

class OllamaClient(LLMClient):
    """Cliente de Ollama (modelos locales). Sin API key ni internet.

    Requiere Ollama corriendo en localhost. Modelos recomendados:
    llama3.1, mistral, qwen2.5, gemma2. Usa la variable OLLAMA_MODEL para
    elegir el modelo (default: llama3.1).
    """

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            import ollama
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "ollama no está instalado. Corré: pip install ollama"
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
                f"Ollama falló (¿está corriendo `ollama serve`?): {exc}"
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
    """Devuelve el cliente LLM activo según COMMUNITYLAB_LLM_BACKEND.

    Si `backend` no se pasa, lee la variable de entorno; si tampoco está,
    usa "rule_based" (seguro, sin credenciales).
    """
    name = backend or os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    client_cls = _BACKENDS.get(name)
    if client_cls is None:
        raise LLMError(
            f"Backend LLM desconocido: {name!r}. Opciones válidas: {sorted(_BACKENDS)}."
        )
    return client_cls()
