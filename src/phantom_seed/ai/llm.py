"""OpenRouter client helpers for structured text and image generation."""

from __future__ import annotations

import base64
import json
import random
import socket
import ssl
import time
from pathlib import Path
from typing import Any, Callable
from urllib import request
from urllib.error import HTTPError, URLError

from pydantic import BaseModel


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns an error response."""


StreamProgressCallback = Callable[[dict[str, Any]], None]


class OpenRouterClient:
    """Minimal OpenRouter client using the OpenAI-compatible chat API."""

    def __init__(self, api_key: str, *, app_name: str = "Phantom Seed") -> None:
        self.api_key = api_key
        self.app_name = app_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout_s = 180
        self.max_retries = 4

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/phantom-seed",
            "X-Title": self.app_name,
        }

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, self.max_retries + 1):
            req = request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.timeout_s) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                raise OpenRouterError(
                    f"OpenRouter request failed ({exc.code}): {details}"
                ) from exc
            except (URLError, ssl.SSLError, socket.timeout, TimeoutError) as exc:
                if attempt >= self.max_retries:
                    raise OpenRouterError(
                        "OpenRouter network request failed after retries: "
                        f"{exc}"
                    ) from exc
                # Short exponential backoff with jitter for transient TLS / network failures.
                delay = min(8.0, 0.8 * (2 ** (attempt - 1))) + random.uniform(0, 0.3)
                time.sleep(delay)
        raise OpenRouterError("OpenRouter request failed without a response")

    def _stream_json(
        self,
        payload: dict[str, Any],
        *,
        on_progress: StreamProgressCallback | None = None,
    ) -> dict[str, Any]:
        payload = {**payload, "stream": True}
        text_chunks: list[str] = []
        usage: dict[str, Any] | None = None
        response_id = ""
        response_model = payload.get("model", "")
        finish_reason = ""
        provider = ""
        received_chars = 0

        for attempt in range(1, self.max_retries + 1):
            req = request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    **self._headers(),
                    "Accept": "text/event-stream",
                },
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.timeout_s) as resp:
                    event_lines: list[str] = []
                    for raw_line in resp:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            if event_lines:
                                payload_text = "\n".join(
                                    part[5:].strip()
                                    for part in event_lines
                                    if part.startswith("data:")
                                ).strip()
                                event_lines.clear()
                                if not payload_text or payload_text == "[DONE]":
                                    continue
                                chunk = json.loads(payload_text)
                                if chunk.get("error"):
                                    message = chunk["error"].get(
                                        "message",
                                        "unknown stream error",
                                    )
                                    raise OpenRouterError(
                                        f"OpenRouter stream failed: {message}"
                                    )
                                response_id = chunk.get("id", response_id)
                                response_model = chunk.get("model", response_model)
                                provider = chunk.get("provider", provider)
                                if chunk.get("usage"):
                                    usage = chunk["usage"]
                                choices = chunk.get("choices") or []
                                if choices:
                                    choice = choices[0]
                                    finish_reason = (
                                        choice.get("finish_reason") or finish_reason
                                    )
                                    delta = choice.get("delta") or {}
                                    content = delta.get("content")
                                    if isinstance(content, str) and content:
                                        text_chunks.append(content)
                                        received_chars += len(content)
                                        if on_progress:
                                            on_progress(
                                                {
                                                    "type": "delta",
                                                    "id": response_id,
                                                    "model": response_model,
                                                    "provider": provider,
                                                    "received_chars": received_chars,
                                                    "approx_completion_tokens": max(
                                                        1, received_chars // 4
                                                    ),
                                                }
                                            )
                            continue
                        if line.startswith(":"):
                            if on_progress:
                                on_progress(
                                    {
                                        "type": "keepalive",
                                        "message": line[1:].strip()
                                        or "OPENROUTER PROCESSING",
                                    }
                                )
                            continue
                        event_lines.append(line)
                    break
            except HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                raise OpenRouterError(
                    f"OpenRouter request failed ({exc.code}): {details}"
                ) from exc
            except (URLError, ssl.SSLError, socket.timeout, TimeoutError) as exc:
                if attempt >= self.max_retries:
                    raise OpenRouterError(
                        "OpenRouter network request failed after retries: "
                        f"{exc}"
                    ) from exc
                if on_progress:
                    on_progress(
                        {
                            "type": "retry",
                            "attempt": attempt,
                            "message": str(exc),
                        }
                    )
                delay = min(8.0, 0.8 * (2 ** (attempt - 1))) + random.uniform(0, 0.3)
                time.sleep(delay)
        else:
            raise OpenRouterError("OpenRouter stream failed without a response")

        content = "".join(text_chunks).strip()
        if on_progress:
            on_progress(
                {
                    "type": "final",
                    "id": response_id,
                    "model": response_model,
                    "provider": provider,
                    "usage": usage or {},
                    "finish_reason": finish_reason,
                    "received_chars": received_chars,
                }
            )
        return {
            "id": response_id,
            "model": response_model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": finish_reason or "stop",
                }
            ],
            "usage": usage or {},
        }

    @staticmethod
    def _content_text(message: dict[str, Any]) -> str:
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts).strip()
        return ""

    def structured_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        schema_model: type[BaseModel],
        temperature: float,
        max_tokens: int,
        reasoning: dict[str, Any] | None = None,
        stream_progress: StreamProgressCallback | None = None,
    ) -> BaseModel:
        schema = schema_model.model_json_schema()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": {
                "allow_fallbacks": False,
                "require_parameters": True,
            },
            "plugins": [
                {"id": "response-healing"},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_model.__name__,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        if reasoning:
            payload["reasoning"] = reasoning
        if stream_progress:
            data = self._stream_json(payload, on_progress=stream_progress)
        else:
            data = self._post_json(payload)
        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("OpenRouter returned no choices")
        content = self._content_text(choices[0]["message"])
        if not content:
            raise OpenRouterError("OpenRouter returned empty structured content")
        return schema_model.model_validate_json(content)

    @staticmethod
    def _image_part(path: Path) -> dict[str, Any]:
        mime = "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{encoded}",
            },
        }

    def image_generation(
        self,
        *,
        model: str,
        prompt: str,
        references: list[Path] | None = None,
        aspect_ratio: str = "2:3",
        size: str | None = None,
    ) -> str:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for ref in references or []:
            if ref.exists():
                content.append(self._image_part(ref))
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "modalities": ["image", "text"],
            "provider": {
                "allow_fallbacks": False,
                "require_parameters": True,
            },
            "image_config": {"aspect_ratio": aspect_ratio},
        }
        if size:
            payload["image_config"]["size"] = size
        data = self._post_json(payload)
        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("OpenRouter image request returned no choices")
        images = choices[0].get("message", {}).get("images") or []
        if not images:
            raise OpenRouterError("OpenRouter image request returned no images")
        image_url = images[0].get("image_url", {}).get("url", "")
        if not image_url.startswith("data:image"):
            raise OpenRouterError("OpenRouter returned an unexpected image payload")
        return image_url
