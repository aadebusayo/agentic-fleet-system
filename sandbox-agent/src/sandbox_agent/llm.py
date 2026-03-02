from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote_plus

import httpx


@dataclass
class LLMSettings:
    provider: str
    failover_enabled: bool
    failover_chain: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    endpoint: str | None
    api_key: str | None
    azure_endpoint: str | None
    azure_api_key: str | None
    azure_deployment: str | None
    azure_api_version: str
    anthropic_endpoint: str
    anthropic_api_key: str | None
    anthropic_version: str
    gemini_endpoint: str | None
    gemini_api_key: str | None
    local_llm_endpoint: str | None
    local_llm_format: str
    local_llm_api_key: str | None

    @staticmethod
    def from_env() -> "LLMSettings":
        provider = os.getenv("AGENT_LLM_PROVIDER", "openai-compatible")
        azure_endpoint = os.getenv("AGENT_AZURE_OPENAI_ENDPOINT") or os.getenv("AGENT_LLM_ENDPOINT")
        azure_key = os.getenv("AGENT_AZURE_OPENAI_API_KEY") or os.getenv("AGENT_LLM_API_KEY")
        return LLMSettings(
            provider=provider,
            failover_enabled=os.getenv("AGENT_LLM_FAILOVER_ENABLED", "true").lower() == "true",
            failover_chain=os.getenv(
                "AGENT_LLM_FAILOVER_CHAIN",
                "openai-compatible,azure-openai,anthropic,gemini,local-endpoint",
            ),
            model=os.getenv("AGENT_LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("AGENT_LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("AGENT_LLM_MAX_TOKENS", "512")),
            timeout_seconds=int(os.getenv("AGENT_LLM_TIMEOUT_SECONDS", "30")),
            endpoint=os.getenv("AGENT_LLM_ENDPOINT"),
            api_key=os.getenv("AGENT_LLM_API_KEY"),
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_key,
            azure_deployment=os.getenv("AGENT_AZURE_OPENAI_DEPLOYMENT"),
            azure_api_version=os.getenv("AGENT_AZURE_OPENAI_API_VERSION", "2024-06-01"),
            anthropic_endpoint=os.getenv("AGENT_ANTHROPIC_ENDPOINT", "https://api.anthropic.com/v1/messages"),
            anthropic_api_key=os.getenv("AGENT_ANTHROPIC_API_KEY") or os.getenv("AGENT_LLM_API_KEY"),
            anthropic_version=os.getenv("AGENT_ANTHROPIC_VERSION", "2023-06-01"),
            gemini_endpoint=os.getenv("AGENT_GEMINI_ENDPOINT"),
            gemini_api_key=os.getenv("AGENT_GEMINI_API_KEY") or os.getenv("AGENT_LLM_API_KEY"),
            local_llm_endpoint=os.getenv("AGENT_LOCAL_LLM_ENDPOINT") or os.getenv("AGENT_LLM_ENDPOINT"),
            local_llm_format=os.getenv("AGENT_LOCAL_LLM_FORMAT", "openai-compatible"),
            local_llm_api_key=os.getenv("AGENT_LOCAL_LLM_API_KEY") or os.getenv("AGENT_LLM_API_KEY"),
        )

    def normalized_failover_chain(self) -> list[str]:
        entries = [segment.strip().lower() for segment in self.failover_chain.split(",") if segment.strip()]
        seen: set[str] = set()
        chain: list[str] = []
        for entry in entries:
            if entry not in seen:
                seen.add(entry)
                chain.append(entry)
        return chain

    def validate(self) -> None:
        if self.failover_enabled:
            chain = self.normalized_failover_chain()
            if not chain:
                raise RuntimeError(
                    "LLM config invalid: AGENT_LLM_FAILOVER_CHAIN must include at least one provider when AGENT_LLM_FAILOVER_ENABLED=true"
                )
            valid_provider_found = False
            errors: list[str] = []
            for provider in chain:
                try:
                    self.validate_provider(provider)
                    valid_provider_found = True
                except RuntimeError as exc:
                    errors.append(str(exc))
            if not valid_provider_found:
                details = "; ".join(errors)
                raise RuntimeError(
                    "LLM config invalid: no providers in AGENT_LLM_FAILOVER_CHAIN are properly configured. "
                    f"Details: {details}"
                )
            return

        self.validate_provider(self.provider)

    def validate_provider(self, provider_name: str) -> None:
        provider = provider_name.lower().strip()
        if provider == "openai-compatible":
            if not self.endpoint or not self.api_key:
                raise RuntimeError(
                    "LLM config invalid: AGENT_LLM_ENDPOINT and AGENT_LLM_API_KEY are required for AGENT_LLM_PROVIDER=openai-compatible"
                )
            return
        if provider == "azure-openai":
            if not self.azure_endpoint or not self.azure_api_key or not self.azure_deployment:
                raise RuntimeError(
                    "LLM config invalid: AGENT_AZURE_OPENAI_ENDPOINT (or AGENT_LLM_ENDPOINT), AGENT_AZURE_OPENAI_API_KEY (or AGENT_LLM_API_KEY), and AGENT_AZURE_OPENAI_DEPLOYMENT are required for AGENT_LLM_PROVIDER=azure-openai"
                )
            return
        if provider == "anthropic":
            if not self.anthropic_api_key:
                raise RuntimeError(
                    "LLM config invalid: AGENT_ANTHROPIC_API_KEY (or AGENT_LLM_API_KEY) is required for AGENT_LLM_PROVIDER=anthropic"
                )
            return
        if provider == "gemini":
            if not self.gemini_api_key:
                raise RuntimeError(
                    "LLM config invalid: AGENT_GEMINI_API_KEY (or AGENT_LLM_API_KEY) is required for AGENT_LLM_PROVIDER=gemini"
                )
            return
        if provider == "local-endpoint":
            if not self.local_llm_endpoint:
                raise RuntimeError(
                    "LLM config invalid: AGENT_LOCAL_LLM_ENDPOINT (or AGENT_LLM_ENDPOINT) is required for AGENT_LLM_PROVIDER=local-endpoint"
                )
            local_format = self.local_llm_format.lower().strip()
            if local_format not in {"openai-compatible", "ollama"}:
                raise RuntimeError(
                    "LLM config invalid: AGENT_LOCAL_LLM_FORMAT must be one of: openai-compatible, ollama"
                )
            return
        if provider == "stub":
            allow_stub = os.getenv("AGENT_ALLOW_STUB_LLM", "false").lower() == "true"
            if not allow_stub:
                raise RuntimeError(
                    "LLM config invalid: stub provider requires AGENT_ALLOW_STUB_LLM=true (intended for test/dev only)"
                )
            return
        raise RuntimeError(f"LLM config invalid: unsupported provider '{provider_name}'")


class LLMClient(Protocol):
    async def complete(self, prompt: str, context: dict[str, Any]) -> str: ...


class StubLLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        return f"stub:{self.settings.model}:{prompt[:64]}"


class OpenAICompatibleClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        if not self.settings.endpoint or not self.settings.api_key:
            raise RuntimeError("AGENT_LLM_ENDPOINT and AGENT_LLM_API_KEY are required for openai-compatible provider")

        payload = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a policy-constrained enterprise task agent.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(self.settings.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"]


class AzureOpenAIClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        if not self.settings.azure_endpoint or not self.settings.azure_api_key or not self.settings.azure_deployment:
            raise RuntimeError(
                "AGENT_AZURE_OPENAI_ENDPOINT (or AGENT_LLM_ENDPOINT), AGENT_AZURE_OPENAI_API_KEY (or AGENT_LLM_API_KEY), and AGENT_AZURE_OPENAI_DEPLOYMENT are required for azure-openai provider"
            )

        base = self.settings.azure_endpoint.rstrip("/")
        deployment = quote_plus(self.settings.azure_deployment)
        url = f"{base}/openai/deployments/{deployment}/chat/completions?api-version={self.settings.azure_api_version}"

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a policy-constrained enterprise task agent.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        headers = {
            "api-key": self.settings.azure_api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"]


class AnthropicClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        if not self.settings.anthropic_api_key:
            raise RuntimeError("AGENT_ANTHROPIC_API_KEY is required for anthropic provider")

        payload = {
            "model": self.settings.model,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": self.settings.anthropic_version,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(self.settings.anthropic_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()

        parts = body.get("content", [])
        if parts and isinstance(parts[0], dict):
            return str(parts[0].get("text", ""))
        raise RuntimeError("anthropic response missing content text")


class GeminiClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("AGENT_GEMINI_API_KEY is required for gemini provider")

        if self.settings.gemini_endpoint:
            url = self.settings.gemini_endpoint.format(model=self.settings.model, key=self.settings.gemini_api_key)
        else:
            model = quote_plus(self.settings.model)
            key = quote_plus(self.settings.gemini_api_key)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.settings.temperature,
                "maxOutputTokens": self.settings.max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()

        candidates = body.get("candidates", [])
        if not candidates:
            raise RuntimeError("gemini response missing candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts and isinstance(parts[0], dict):
            return str(parts[0].get("text", ""))
        raise RuntimeError("gemini response missing text")


class LocalEndpointClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        if not self.settings.local_llm_endpoint:
            raise RuntimeError("AGENT_LOCAL_LLM_ENDPOINT is required for local-endpoint provider")

        local_format = self.settings.local_llm_format.lower().strip()
        endpoint = self.settings.local_llm_endpoint

        if local_format == "openai-compatible":
            payload = {
                "model": self.settings.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a policy-constrained enterprise task agent.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            }
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self.settings.local_llm_api_key:
                headers["Authorization"] = f"Bearer {self.settings.local_llm_api_key}"

            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
            return body["choices"][0]["message"]["content"]

        if local_format == "ollama":
            payload = {
                "model": self.settings.model,
                "messages": [
                    {"role": "system", "content": "You are a policy-constrained enterprise task agent."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": self.settings.temperature,
                    "num_predict": self.settings.max_tokens,
                },
            }

            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                body = response.json()

            message = body.get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
            raise RuntimeError("local ollama response missing message.content")

        raise RuntimeError(f"unsupported local format: {self.settings.local_llm_format}")


class FailoverLLMClient:
    def __init__(self, settings: LLMSettings, failover_chain: list[str]) -> None:
        self.settings = settings
        self.failover_chain = failover_chain
        self._clients: dict[str, LLMClient] = {}

    def _get_client(self, provider: str) -> LLMClient:
        if provider not in self._clients:
            self._clients[provider] = build_provider_client(self.settings, provider)
        return self._clients[provider]

    async def complete(self, prompt: str, context: dict[str, Any]) -> str:
        errors: list[str] = []
        for provider in self.failover_chain:
            try:
                self.settings.validate_provider(provider)
            except RuntimeError as exc:
                errors.append(f"{provider}: {exc}")
                continue

            client = self._get_client(provider)
            try:
                return await client.complete(prompt, context)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        detail = " | ".join(errors)
        raise RuntimeError(
            "all failover providers failed; checked AGENT_LLM_FAILOVER_CHAIN in order "
            f"[{', '.join(self.failover_chain)}]. Details: {detail}"
        )


def build_provider_client(settings: LLMSettings, provider_name: str) -> LLMClient:
    provider = provider_name.lower().strip()
    if provider == "openai-compatible":
        return OpenAICompatibleClient(settings)
    if provider == "azure-openai":
        return AzureOpenAIClient(settings)
    if provider == "anthropic":
        return AnthropicClient(settings)
    if provider == "gemini":
        return GeminiClient(settings)
    if provider == "local-endpoint":
        return LocalEndpointClient(settings)
    if provider == "stub":
        return StubLLMClient(settings)
    raise RuntimeError(f"unsupported provider: {provider_name}")


def build_llm_client(settings: LLMSettings) -> LLMClient:
    if settings.failover_enabled:
        return FailoverLLMClient(settings, settings.normalized_failover_chain())
    return build_provider_client(settings, settings.provider)
