"""SAP AI Core adapter using the sap-ai-sdk-gen OpenAI proxy (vendored for Bekaert)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

def _get_chat_api():
    """Lazily import the SAP Generative AI Hub OpenAI proxy to avoid hard import failures at module import time."""
    try:  # Prefer the current sap-ai-sdk-gen namespace
        from gen_ai_hub.proxy.native.openai import chat as chat_api  # type: ignore
        return chat_api
    except ImportError as exc_new:  # Fallback to legacy package name
        try:
            from generative_ai_hub.proxy.native.openai import chat as chat_api  # type: ignore
            return chat_api
        except ImportError as exc_old:  # pragma: no cover - surface actionable guidance
            raise ImportError(
                "SAP Generative AI Hub SDK not found.\n"
                "Install via: pip install sap-ai-sdk-gen"
            ) from (exc_new or exc_old)

DEFAULT_TEMPERATURE = 0.2


@dataclass
class AICoreConfig:
    base_url: str
    auth_url: str
    resource_group: str
    deployment_id: str
    client_id: str
    client_secret: str
    temperature: float = DEFAULT_TEMPERATURE


class AICoreChatLLM:
    """Wrap SAP's ChatCompletions proxy for the document pipeline."""

    def __init__(self, config: AICoreConfig) -> None:
        self.config = config
        self._ensure_env()

    @classmethod
    def from_env(cls) -> "AICoreChatLLM":
        base_url = os.getenv("AICORE_BASE_URL")
        auth_url = os.getenv("AICORE_AUTH_URL")
        resource_group = os.getenv("AICORE_RESOURCE_GROUP")
        deployment_id = os.getenv("AICORE_DEPLOYMENT_ID")
        client_id = os.getenv("AICORE_CLIENT_ID")
        client_secret = os.getenv("AICORE_CLIENT_SECRET")
        temperature = float(os.getenv("AICORE_TEMPERATURE", DEFAULT_TEMPERATURE))

        missing = {
            name: value
            for name, value in {
                "AICORE_BASE_URL": base_url,
                "AICORE_AUTH_URL": auth_url,
                "AICORE_DEPLOYMENT_ID": deployment_id,
                "AICORE_CLIENT_ID": client_id,
                "AICORE_CLIENT_SECRET": client_secret,
            }.items()
            if not value
        }
        if missing:
            joined = ", ".join(sorted(missing.keys()))
            raise EnvironmentError(f"Missing required AI Core environment variables: {joined}")

        cfg = AICoreConfig(
            base_url=base_url.rstrip("/"),
            auth_url=auth_url.rstrip("/"),
            resource_group=(resource_group.strip() if resource_group else "default"),
            deployment_id=deployment_id,
            client_id=client_id,
            client_secret=client_secret,
            temperature=temperature,
        )
        return cls(cfg)

    def _ensure_env(self) -> None:
        env_overrides = {
            "GEN_AI_HUB_BASE_URL": self.config.base_url,
            "GEN_AI_HUB_AUTH_URL": self.config.auth_url,
            "GEN_AI_HUB_RESOURCE_GROUP": self.config.resource_group,
            "GEN_AI_HUB_CLIENT_ID": self.config.client_id,
            "GEN_AI_HUB_CLIENT_SECRET": self.config.client_secret,
            "AI_API_URL": self.config.base_url,
            "AI_API_RESOURCE_GROUP": self.config.resource_group,
            "AI_API_CLIENT_ID": self.config.client_id,
            "AI_API_CLIENT_SECRET": self.config.client_secret,
        }

        for key, value in env_overrides.items():
            if value:
                os.environ.setdefault(key, value)

    def generate(self, messages: Iterable[Dict[str, Any]]) -> str:
        payload_messages = self._format_messages(messages)
        try:
            chat = _get_chat_api()
            response = chat.completions.create(  # type: ignore[attr-defined]
                model_name=self.config.deployment_id or "gpt-5",
                messages=payload_messages,
                temperature=self.config.temperature,
            )
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"AI Core LLM call failed: {exc}") from exc

        content = self._extract_content(response)
        if content is None:
            raise RuntimeError(f"AI Core response missing assistant content: {response}")
        return content

    def invoke(self, prompt: str) -> str:
        return self.generate([{"role": "user", "content": prompt}])

    @staticmethod
    def _format_messages(messages: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
        formatted: List[Dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", "user")).lower()
            if role not in {"system", "user", "assistant"}:
                role = "user"
            content = str(message.get("content", ""))
            formatted.append({"role": role, "content": content})
        return formatted

    @staticmethod
    def _extract_content(response: Any) -> Optional[str]:
        choices = None
        if hasattr(response, "choices"):
            choices = getattr(response, "choices", None)
        elif isinstance(response, dict):
            choices = response.get("choices")

        if not choices:
            return None

        choice = choices[0]

        message = None
        if isinstance(choice, dict):
            message = choice.get("message") or choice.get("delta")
        else:
            message = getattr(choice, "message", None) or getattr(choice, "delta", None)

        content = None
        if isinstance(message, dict):
            content = message.get("content")
        elif message is not None and hasattr(message, "content"):
            content = getattr(message, "content")

        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", ""))
                else:
                    parts.append(str(block))
            content = "".join(parts)

        if isinstance(content, str):
            return content

        if isinstance(choice, dict):
            return str(choice.get("text") or choice)
        if hasattr(choice, "text") and getattr(choice, "text"):
            return str(getattr(choice, "text"))

        return None


__all__ = ["AICoreChatLLM", "AICoreConfig"]
