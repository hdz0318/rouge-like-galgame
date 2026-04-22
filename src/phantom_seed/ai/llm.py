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
from pydantic import ValidationError
from pydantic_core import ValidationError as CoreValidationError


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns an error response."""


ProgressCallback = Callable[[dict[str, Any]], None]


class OpenRouterClient:
    """Minimal OpenRouter client using the OpenAI-compatible chat API."""

    def __init__(self, api_key: str, *, app_name: str = "Phantom Seed") -> None:
        self.api_key = api_key
        self.app_name = app_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout_s = 45
        self.max_retries = 1

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

    @staticmethod
    def _supports_strict_json_schema(model: str) -> bool:
        lowered = model.lower()
        return (
            lowered.startswith("openai/")
            or lowered.startswith("anthropic/")
            or lowered.startswith("google/")
        )

    @classmethod
    def _normalize_json_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        defs = schema.get("$defs", {})

        def deref(node: Any) -> Any:
            if isinstance(node, dict):
                if "$ref" in node:
                    ref = node["$ref"]
                    if isinstance(ref, str) and ref.startswith("#/$defs/"):
                        key = ref.split("/")[-1]
                        target = defs.get(key)
                        if target is None:
                            return {}
                        return deref(target)
                return {key: deref(value) for key, value in node.items() if key != "$defs"}
            if isinstance(node, list):
                return [deref(item) for item in node]
            return node

        def visit(node: Any) -> Any:
            if isinstance(node, dict):
                normalized = {key: visit(value) for key, value in node.items()}
                properties = normalized.get("properties")
                if isinstance(properties, dict):
                    normalized["required"] = list(properties.keys())
                    normalized.setdefault("additionalProperties", False)
                    for key, value in list(properties.items()):
                        if isinstance(value, dict) and "default" in value:
                            value = dict(value)
                            value.pop("default", None)
                            properties[key] = value
                return normalized
            if isinstance(node, list):
                return [visit(item) for item in node]
            return node

        expanded = deref(schema)
        expanded.pop("$defs", None)
        return visit(expanded)

    def structured_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        schema_model: type[BaseModel],
        temperature: float,
        max_tokens: int,
        stream_progress: ProgressCallback | None = None,
    ) -> BaseModel:
        supports_json_schema = self._supports_strict_json_schema(model)
        schema = self._normalize_json_schema(schema_model.model_json_schema())
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": {
                "allow_fallbacks": False,
                "require_parameters": supports_json_schema,
            },
        }
        payload["plugins"] = [
            {"id": "response-healing"},
        ]
        if supports_json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_model.__name__,
                    "strict": True,
                    "schema": schema,
                },
            }
        else:
            payload["response_format"] = {"type": "json_object"}
        if stream_progress:
            stream_progress(
                {
                    "type": "keepalive",
                    "message": (
                        "structured json_schema request in progress"
                        if supports_json_schema
                        else "json_object request in progress"
                    ),
                }
            )
        data = self._post_json(payload)
        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("OpenRouter returned no choices")
        content = self._content_text(choices[0]["message"])
        if not content:
            raise OpenRouterError("OpenRouter returned empty structured content")
        if stream_progress:
            stream_progress(
                {
                    "type": "final",
                    "usage": data.get("usage") or {},
                    "finish_reason": choices[0].get("finish_reason", "stop"),
                    "received_chars": len(content),
                }
            )
        try:
            return schema_model.model_validate_json(content)
        except (ValidationError, CoreValidationError) as exc:
            preview = content[:240].replace("\n", "\\n")
            raise OpenRouterError(
                f"Structured output validation failed: {exc}. content_preview={preview}"
            ) from exc

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
        message = choices[0].get("message", {}) or {}
        images = message.get("images") or []
        if not images:
            content = self._content_text(message)
            refusal = message.get("refusal", "")
            details: list[str] = []
            if content:
                details.append(f"content={content[:240]}")
            if refusal:
                details.append(f"refusal={str(refusal)[:240]}")
            if choices[0].get("finish_reason"):
                details.append(f"finish_reason={choices[0]['finish_reason']}")
            detail_suffix = f" ({'; '.join(details)})" if details else ""
            raise OpenRouterError(
                "OpenRouter image request returned no images" + detail_suffix
            )
        image_url = images[0].get("image_url", {}).get("url", "")
        if not image_url.startswith("data:image"):
            raise OpenRouterError("OpenRouter returned an unexpected image payload")
        return image_url
