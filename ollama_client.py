"""
ollama_client.py – Unified IBM Granite / Ollama client.

Provides connection-status checking and text generation.
Configuration is read from environment variables (.env file) so no
secrets are hard-coded.  Runtime overrides are supported via
set_config() for the Settings page.
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration – read from .env or use sensible defaults
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "granite4.2:3b")

# Runtime-overridable values (updated by set_config)
_runtime_url: str = OLLAMA_BASE_URL
_runtime_model: str = OLLAMA_MODEL


def set_config(url: str = "", model: str = "") -> None:
    """Override the Ollama URL and/or model at runtime (from Settings page)."""
    global _runtime_url, _runtime_model
    if url.strip():
        _runtime_url = url.strip()
    if model.strip():
        _runtime_model = model.strip()


def get_config() -> dict:
    """Return the current effective URL and model."""
    return {"url": _runtime_url, "model": _runtime_model}


def _tags_url() -> str:
    return f"{_runtime_url}/api/tags"


def _generate_url() -> str:
    return f"{_runtime_url}/api/generate"


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """
    Return a dict describing the current Ollama / Granite status.

    Keys
    ----
    ollama_online   : bool
    model_available : bool
    model_name      : str
    available_models: list[str]
    error           : str | None
    """
    status = {
        "ollama_online": False,
        "model_available": False,
        "model_name": _runtime_model,
        "available_models": [],
        "error": None,
    }

    try:
        resp = requests.get(_tags_url(), timeout=5)
        resp.raise_for_status()
        status["ollama_online"] = True

        models_data = resp.json().get("models", [])
        status["available_models"] = [m.get("name", "") for m in models_data]

        # Match configured model (prefix match for tag flexibility)
        configured = _runtime_model.lower()
        for name in status["available_models"]:
            if name.lower().startswith(configured.split(":")[0]):
                status["model_available"] = True
                status["model_name"] = name
                break

    except requests.exceptions.ConnectionError:
        status["error"] = (
            f"Cannot reach Ollama at {_runtime_url}. "
            "Make sure Ollama is running: ollama serve"
        )
    except Exception as exc:
        status["error"] = str(exc)

    return status


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

def generate(prompt: str, timeout: int = 300) -> str:
    """
    Send *prompt* to IBM Granite via Ollama and return the response text.

    Raises
    ------
    RuntimeError – Ollama not reachable, model missing, or empty reply.
    """
    status = get_status()

    if not status["ollama_online"]:
        raise RuntimeError(
            f"Ollama is not running. Start it with: ollama serve\n"
            f"({status['error']})"
        )

    if not status["model_available"]:
        available = ", ".join(status["available_models"]) or "none"
        raise RuntimeError(
            f"Model '{_runtime_model}' is not available in Ollama.\n"
            f"Available models: {available}\n"
            f"Pull it with: ollama pull {_runtime_model}"
        )

    model_to_use = status["model_name"]

    try:
        resp = requests.post(
            _generate_url(),
            json={
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "IBM Granite took too long to respond. "
            "Try a shorter prompt or increase the timeout."
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Lost connection to Ollama at {_runtime_url}."
        )

    result = resp.json().get("response", "").strip()
    if not result:
        raise RuntimeError("IBM Granite returned an empty response.")

    logger.info("Granite generate OK (%d chars)", len(result))
    return result
