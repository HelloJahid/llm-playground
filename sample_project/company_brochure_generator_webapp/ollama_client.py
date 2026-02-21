"""
ollama_client.py
----------------
Thin HTTP client for the locally-running Ollama inference server.
Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import json
from typing import Generator

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
_GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"
_TAGS_ENDPOINT = f"{OLLAMA_BASE_URL}/api/tags"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OllamaConnectionError(RuntimeError):
    """Raised when Ollama cannot be reached on the local port."""


class OllamaResponseError(RuntimeError):
    """Raised when Ollama returns an unexpected / error response."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ollama_generate(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.4,
    timeout: float = 120.0,
) -> str:
    """
    Call the Ollama ``/api/generate`` endpoint and return the complete
    response text as a single string (non-streaming mode).

    Parameters
    ----------
    model:
        Ollama model tag, e.g. ``"llama3.1:8b"`` or ``"mistral"``.
    prompt:
        The user-facing prompt to send.
    system:
        Optional system message that sets the model's behaviour/persona.
    temperature:
        Sampling temperature (0 = deterministic, 1 = very creative).
    timeout:
        HTTP timeout in seconds.  Generation of long brochures may need
        more than the default 30 s, so this defaults to 120 s.

    Returns
    -------
    str
        The model's response text, stripped of leading/trailing whitespace.

    Raises
    ------
    OllamaConnectionError
        If Ollama is not running or not reachable at ``localhost:11434``.
    OllamaResponseError
        If the HTTP response indicates an error or the JSON is malformed.
    """
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            _GENERATE_ENDPOINT,
            json=payload,
            timeout=timeout,
        )
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            "Cannot connect to Ollama at http://localhost:11434. "
            "Make sure Ollama is installed and running (`ollama serve`)."
        ) from exc
    except requests.Timeout as exc:
        raise OllamaConnectionError(
            f"Request to Ollama timed out after {timeout} seconds. "
            "Try a smaller model or increase the timeout."
        ) from exc

    # Non-2xx status
    if not resp.ok:
        try:
            detail = resp.json().get("error", resp.text)
        except ValueError:
            detail = resp.text
        raise OllamaResponseError(
            f"Ollama returned HTTP {resp.status_code}: {detail}"
        )

    # Parse JSON response
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise OllamaResponseError(
            f"Ollama response was not valid JSON: {resp.text[:200]}"
        ) from exc

    response_text: str = data.get("response", "")
    if not response_text:
        raise OllamaResponseError(
            "Ollama returned an empty 'response' field. "
            f"Full payload: {json.dumps(data)[:300]}"
        )

    return response_text.strip()


def ollama_stream(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.4,
    timeout: float = 120.0,
) -> Generator[str, None, None]:
    """
    Call Ollama in *streaming* mode and yield each text chunk as it arrives.

    Useful for updating a Streamlit ``st.empty()`` placeholder in real time
    without waiting for the full response.

    Yields
    ------
    str
        Incremental text chunks from the model.

    Raises
    ------
    OllamaConnectionError / OllamaResponseError
        Same conditions as ``ollama_generate``.
    """
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    try:
        with requests.post(
            _GENERATE_ENDPOINT,
            json=payload,
            stream=True,
            timeout=timeout,
        ) as resp:
            if not resp.ok:
                try:
                    detail = resp.json().get("error", resp.text)
                except ValueError:
                    detail = resp.text
                raise OllamaResponseError(
                    f"Ollama returned HTTP {resp.status_code}: {detail}"
                )

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue  # skip malformed lines

                token = chunk.get("response", "")
                if token:
                    yield token

                # The final chunk has done=true; nothing more to yield
                if chunk.get("done"):
                    break

    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            "Cannot connect to Ollama at http://localhost:11434. "
            "Make sure Ollama is installed and running (`ollama serve`)."
        ) from exc
    except requests.Timeout as exc:
        raise OllamaConnectionError(
            f"Streaming request to Ollama timed out after {timeout} s."
        ) from exc


def list_local_models() -> list[str]:
    """
    Return a list of model tags currently available in the local Ollama
    instance (e.g. ``["llama3.1:8b", "mistral:latest"]``).

    Returns an empty list if Ollama is not running (does not raise).
    """
    try:
        resp = requests.get(_TAGS_ENDPOINT, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        # Silently return empty list so callers can handle it gracefully
        return []


def check_ollama_running() -> bool:
    """Return ``True`` if Ollama is reachable, ``False`` otherwise."""
    try:
        resp = requests.get(OLLAMA_BASE_URL, timeout=3.0)
        return resp.ok
    except Exception:
        return False
