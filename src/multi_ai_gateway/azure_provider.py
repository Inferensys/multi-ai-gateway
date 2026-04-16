from __future__ import annotations

import time

from openai import AzureOpenAI

from .config import Settings
from .models import ChatMessage


class AzureChatProvider:
    def __init__(self, settings: Settings) -> None:
        settings.validate_for_azure()
        self._settings = settings
        self._client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            max_retries=2,
            timeout=settings.request_timeout_seconds,
        )

    def complete(self, *, deployment: str, messages: list[ChatMessage], max_output_tokens: int) -> dict:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=deployment,
            messages=[{"role": message.role, "content": message.content} for message in messages],
            max_completion_tokens=max_output_tokens,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        message = response.choices[0].message
        usage = getattr(response, "usage", None)
        return {
            "output_text": (message.content or "").strip(),
            "finish_reason": response.choices[0].finish_reason,
            "latency_ms": latency_ms,
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
