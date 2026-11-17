"""Google Gemini client used by the travel agents."""

from typing import Optional
import json
import os
import socket
import urllib.error
import urllib.request


class LLMServiceError(RuntimeError):
    """Base error for failures communicating with the configured language model."""

    status_code = 502


class LLMConfigurationError(LLMServiceError):
    status_code = 503


class LLMRateLimitError(LLMServiceError):
    status_code = 429


class LLMTimeoutError(LLMServiceError):
    status_code = 504


class LLMInvalidResponseError(LLMServiceError):
    status_code = 502


class GeminiLLMService:
    """Client for Gemini's generateContent API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.8-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # Sanitize model name - strip whitespace and any leading 'models/' prefix if present
        clean_model = (model or "gemini-3.8-flash").strip()
        if clean_model.startswith("models/"):
            clean_model = clean_model[len("models/"):]
        if not clean_model or clean_model.startswith("YOUR_") or clean_model.startswith("your_"):
            clean_model = "gemini-3.8-flash"
        self.model = clean_model
        self.api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

    def is_configured(self) -> bool:
        key = (self.api_key or "").strip()
        return bool(key and not key.startswith("your_") and not key.startswith("YOUR_"))

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        allow_offline_fallback: bool = True
    ) -> str:
        """Generate text, optionally preserving the legacy, clearly labeled offline demo."""
        if not self.is_configured():
            if allow_offline_fallback:
                return self._simulate_real_llm_response(prompt)
            raise LLMConfigurationError(
                "Gemini is not configured. Set GEMINI_API_KEY to enable AI chat."
            )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }
        request = urllib.request.Request(
            f"{self.api_url}?key={self.api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                try:
                    result = json.loads(response.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise LLMInvalidResponseError(
                        "Gemini returned an unreadable response."
                    ) from exc
        except urllib.error.HTTPError as exc:
            # Safely read error body from provider without leaking secrets
            error_body = ""
            error_detail = ""
            try:
                error_body = exc.read().decode("utf-8")
                err_json = json.loads(error_body)
                if isinstance(err_json, dict) and "error" in err_json:
                    error_detail = err_json["error"].get("message", "")
            except Exception:
                pass

            if exc.code == 404:
                msg = f"Gemini model '{self.model}' not found (HTTP 404)."
                if error_detail:
                    msg += f" Details: {error_detail}"
                raise LLMConfigurationError(msg) from exc
            if exc.code == 429:
                raise LLMRateLimitError(
                    "Gemini is rate-limiting requests. Please wait and try again."
                ) from exc
            if exc.code in (401, 403):
                msg = "Gemini rejected the API key. Check GEMINI_API_KEY and its permissions."
                if error_detail:
                    msg += f" Details: {error_detail}"
                raise LLMConfigurationError(msg) from exc
            if exc.code in (408, 504):
                raise LLMTimeoutError(
                    "Gemini timed out. Please try again."
                ) from exc
            error_msg = f"Gemini request failed with HTTP {exc.code}."
            if error_detail:
                error_msg += f" Details: {error_detail}"
            raise LLMServiceError(error_msg) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise LLMTimeoutError(
                "Gemini timed out. Please try again."
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise LLMTimeoutError(
                    "Gemini timed out. Please try again."
                ) from exc
            raise LLMServiceError(
                "Could not connect to Gemini. Check the network and try again."
            ) from exc

        candidates = result.get("candidates") if isinstance(result, dict) else None
        if not isinstance(candidates, list) or not candidates:
            raise LLMInvalidResponseError(
                "Gemini did not return a response. Please rephrase your message and try again."
            )

        candidate = candidates[0]
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise LLMInvalidResponseError(
                "Gemini returned an invalid response. Please try again."
            )
        text = "\n".join(
            part["text"] for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
        if not text:
            raise LLMInvalidResponseError(
                "Gemini returned an empty response. Please try again."
            )
        return text

    def _simulate_real_llm_response(self, prompt: str) -> str:
        """Predictable demo for legacy agent tests; never presented as a Gemini answer."""
        lower = prompt.lower()
        offline_label = "[OFFLINE SIMULATION - NOT GENERATED BY GEMINI]"

        def labeled(response: str) -> str:
            return f"{offline_label}\n{response}"

        if "tokyo" in lower:
            if "observation:" not in lower:
                return labeled(
                    "Thought: I will first check the weather forecast for Tokyo.\n"
                    'Action: get_weather_forecast(city="Tokyo", days=3)'
                )
            if "partly cloudy" in lower and "senso-ji" not in lower:
                return labeled(
                    "Thought: The weather in Tokyo is mild. Next, I will search attractions.\n"
                    'Action: search_destinations_and_attractions(city="Tokyo", category="culture")'
                )
            if "senso-ji" in lower and "nine hours" not in lower:
                return labeled(
                    "Thought: I found cultural attractions. Now looking for hotels.\n"
                    'Action: search_hotels(city="Tokyo", budget_tier="mid", nights=3, guests=2)'
                )
            return labeled(
                "Thought: I have gathered the available information.\n"
                "Final Answer: Here is a demo 3-day Tokyo itinerary featuring Senso-ji Temple "
                "and Shibuya."
            )
        return labeled(
            "Thought: Processing the travel request in offline demo mode.\n"
            "Final Answer: Travel demo ready."
        )
