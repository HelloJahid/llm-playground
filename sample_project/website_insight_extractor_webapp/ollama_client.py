"""
ollama_client.py
----------------
Minimal HTTP client for the locally-running Ollama inference server.
API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import json

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
_GENERATE_URL   = f"{OLLAMA_BASE_URL}/api/generate"
_TAGS_URL       = f"{OLLAMA_BASE_URL}/api/tags"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OllamaConnectionError(RuntimeError):
    """Ollama server is not reachable on localhost:11434."""


class OllamaResponseError(RuntimeError):
    """Ollama returned an unexpected or error response."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ollama_generate(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> str:
    """
    Send a prompt to Ollama and return the complete response text.

    Uses non-streaming mode (``"stream": false``) so the full answer arrives
    in a single JSON response — simpler and more reliable for structured output.

    Parameters
    ----------
    model:
        Ollama model tag, e.g. ``"llama3.1:8b"``.
    prompt:
        The user-facing prompt text.
    system:
        Optional system message that shapes the model's behaviour.
    temperature:
        Sampling temperature.  0.2 keeps answers factual and grounded.
    timeout:
        HTTP timeout in seconds.  Increase for larger models / longer pages.

    Returns
    -------
    str
        Stripped response text from the model.

    Raises
    ------
    OllamaConnectionError
        If Ollama is not running or the port is blocked.
    OllamaResponseError
        On HTTP errors or unexpected JSON structure.
    """
    payload: dict = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(_GENERATE_URL, json=payload, timeout=timeout)
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            "Cannot reach Ollama at http://localhost:11434. "
            "Run `ollama serve` in a terminal and try again."
        ) from exc
    except requests.Timeout as exc:
        raise OllamaConnectionError(
            f"Ollama did not respond within {timeout:.0f} s. "
            "Try a smaller/faster model or increase the timeout."
        ) from exc

    if not resp.ok:
        try:
            detail = resp.json().get("error", resp.text)
        except ValueError:
            detail = resp.text
        raise OllamaResponseError(
            f"Ollama returned HTTP {resp.status_code}: {detail}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise OllamaResponseError(
            f"Ollama response was not valid JSON: {resp.text[:300]}"
        ) from exc

    text: str = data.get("response", "")
    if not text:
        raise OllamaResponseError(
            "Ollama returned an empty 'response' field. "
            f"Raw payload: {json.dumps(data)[:300]}"
        )

    return text.strip()


def list_local_models() -> list[str]:
    """
    Return the names of models already pulled to the local Ollama instance.
    Returns an empty list silently if Ollama is not running.
    """
    try:
        resp = requests.get(_TAGS_URL, timeout=4.0)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def check_ollama_running() -> bool:
    """Return True if Ollama is reachable, False otherwise."""
    try:
        return requests.get(OLLAMA_BASE_URL, timeout=3.0).ok
    except Exception:
        return False
