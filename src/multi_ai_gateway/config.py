from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DeploymentProfile:
    name: str
    quality_tier: int
    speed_tier: int
    cost_tier: int
    max_output_tokens: int
    notes: str


@dataclass(frozen=True)
class Settings:
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2025-04-01-preview"
    request_timeout_seconds: float = 90.0
    fast_deployment: str = "gpt-5-mini"
    quality_deployment: str = "gpt-5.4"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
            request_timeout_seconds=float(os.getenv("MULTI_AI_GATEWAY_TIMEOUT_SECONDS", "90")),
            fast_deployment=os.getenv("MULTI_AI_GATEWAY_FAST_DEPLOYMENT", "gpt-5-mini"),
            quality_deployment=os.getenv("MULTI_AI_GATEWAY_QUALITY_DEPLOYMENT", "gpt-5.4"),
        )

    def validate_for_azure(self) -> None:
        missing: list[str] = []
        if not self.azure_openai_endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self.azure_openai_api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if missing:
            raise RuntimeError(
                "Azure gateway mode requires environment variables: "
                + ", ".join(missing)
            )

    def default_deployments(self) -> list[DeploymentProfile]:
        return [
            DeploymentProfile(
                name=self.fast_deployment,
                quality_tier=2,
                speed_tier=5,
                cost_tier=1,
                max_output_tokens=900,
                notes="Fast path for low-risk or latency-sensitive traffic.",
            ),
            DeploymentProfile(
                name=self.quality_deployment,
                quality_tier=5,
                speed_tier=2,
                cost_tier=3,
                max_output_tokens=1800,
                notes="Heavy path for reasoning-heavy or high-risk requests.",
            ),
        ]
