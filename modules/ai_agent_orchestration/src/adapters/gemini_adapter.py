import os
from pathlib import Path
import logging
import time
from typing import List, Dict, Any, Optional
import httpx

from modules.ai_agent_orchestration.src.adapters.llm_adapter import LLMAdapter
from modules.ai_agent_orchestration.src.adapters.offline_teacher import offline_reply

logger = logging.getLogger(__name__)

# A full teaching segment (up to ~600 spoken words plus notes and a visual spec)
# needs real headroom, and a long JSON reply needs longer than a chat turn.
MAX_OUTPUT_TOKENS = 8192
REQUEST_TIMEOUT_SEC = 90.0
# Free-tier keys hit 429s routinely; a short wait usually clears them, and
# anything longer is worse for the learner than the offline fallback.
RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS_SEC = (2.0, 5.0)
MAX_RETRY_AFTER_SEC = 10.0
# After Gemini fails even with retries (e.g. the free-tier quota is used up),
# skip it for this long instead of making every learner wait ~9 s of retries
# on every step. The offline teacher serves those steps.
FAILURE_COOLDOWN_SEC = 60.0
_cooldown = {"until": 0.0}


class SmartMockLLMAdapter(LLMAdapter):
    """
    Deterministic fallback LLM: builds contract-valid replies from the request
    context (see offline_teacher.py). Used with no key and whenever a live call fails.
    """

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        return offline_reply(messages)


def _load_env():
    """Silently populate os.environ from root .env if present and not already set."""
    # Find project root (4 levels up from modules/ai_agent_orchestration/src/adapters/gemini_adapter.py)
    root = Path(__file__).resolve().parent.parent.parent.parent.parent
    env_file = root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


class GeminiLLMAdapter(LLMAdapter):
    """
    Live Google Gemini LLM adapter conforming to Contract §14.
    Reads API key exclusively from runtime environment (os.environ).
    Gracefully falls back to SmartMockLLMAdapter if network/key issues occur.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash-lite", raise_on_failure: bool = False):
        _load_env()
        # None means "look the key up"; an explicit empty string means "no key",
        # so callers can force the offline path without the ambient environment
        # quietly supplying one.
        self.api_key = (
            os.environ.get("GEMINI_API_KEY", "") if api_key is None else api_key
        ).strip()
        self.model = os.environ.get("GEMINI_MODEL", model)
        self.raise_on_failure = raise_on_failure
        self.fallback = SmartMockLLMAdapter()

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.api_key:
            if self.raise_on_failure:
                raise ValueError("LIVE GEMINI mode selected but GEMINI_API_KEY is not set.")
            logger.info("No GEMINI_API_KEY set; using SmartMockLLMAdapter.")
            return self.fallback.complete(messages, tools)

        if not self.raise_on_failure and time.monotonic() < _cooldown["until"]:
            return self.fallback.complete(messages, tools)

        # Build contents from messages
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "model" if role in ("assistant", "model") else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })

        # The key goes in a header, never the query string: httpx logs the full
        # request URL at INFO, so ?key=... wrote the secret into the server log
        # (and into Render's retained logs) on every single call.
        headers = {"x-goog-api-key": self.api_key}
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                # A full-length teaching script plus its notes runs well past the
                # small default, and a truncated reply comes back with no parts
                # at all, which used to look like "the model returned nothing".
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # An optional second model (e.g. a lighter one with its own quota) is
        # tried before giving up and teaching from the offline fallback.
        fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", "").strip()
        models_to_try = [self.model] + ([fallback_model] if fallback_model and fallback_model != self.model else [])
        last_error: Optional[Exception] = None

        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                resp = self._post_with_retry(url, headers, payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
                # Falling through here silently served mock content as if it
                # were the model's. Say why, so a truncated or blocked reply
                # is visible in the log instead of looking like a short lesson.
                reason = (candidates[0].get("finishReason") if candidates else None) or "no candidates"
                logger.warning(
                    "Gemini '%s' returned no usable text (finishReason=%s, prompt_feedback=%s)",
                    m, reason, data.get("promptFeedback"),
                )
                last_error = RuntimeError(f"empty response (finishReason={reason})")
            except Exception as e:
                logger.warning(f"Live Gemini call for '{m}' failed ({e}).")
                last_error = e

        if self.raise_on_failure:
            raise RuntimeError(f"LIVE GEMINI failure: All models failed. Last error: {last_error}")
        _cooldown["until"] = time.monotonic() + FAILURE_COOLDOWN_SEC
        logger.warning(
            "Gemini unavailable (%s); using the offline teacher for the next %.0fs.",
            last_error, FAILURE_COOLDOWN_SEC,
        )
        return self.fallback.complete(messages, tools)

    def _post_with_retry(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> httpx.Response:
        """POST, retrying rate limits, transient 5xx and network errors briefly."""
        attempt = 0
        while True:
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
                    resp = client.post(url, headers=headers, json=payload)
            except (httpx.TransportError,) as exc:
                if attempt >= len(RETRY_DELAYS_SEC):
                    raise
                delay = RETRY_DELAYS_SEC[attempt]
                logger.info("Gemini network error (%s); retrying in %.0fs", exc, delay)
            else:
                if resp.status_code not in RETRY_STATUSES or attempt >= len(RETRY_DELAYS_SEC):
                    return resp
                delay = RETRY_DELAYS_SEC[attempt]
                try:
                    delay = min(MAX_RETRY_AFTER_SEC, max(delay, float(resp.headers.get("retry-after", 0))))
                except ValueError:
                    pass
                logger.info("Gemini returned %s; retrying in %.0fs", resp.status_code, delay)
            time.sleep(delay)
            attempt += 1


def get_llm_adapter(api_key: Optional[str] = None) -> LLMAdapter:
    """Factory creating GeminiLLMAdapter if GEMINI_API_KEY is available, else SmartMockLLMAdapter."""
    _load_env()
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if key and key.strip():
        return GeminiLLMAdapter(api_key=key.strip())
    return SmartMockLLMAdapter()
