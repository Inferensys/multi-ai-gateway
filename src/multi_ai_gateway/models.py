from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


RoutingMode = Literal["latency", "balanced", "quality"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class GatewayRequest:
    messages: list[ChatMessage]
    routing_mode: RoutingMode = "balanced"
    risk_level: RiskLevel = "medium"
    requires_json: bool = False
    max_cost_tier: int | None = None
    allowed_deployments: list[str] | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteDecision:
    selected_deployment: str
    fallback_chain: list[str]
    rationale: str
    routing_mode: RoutingMode
    risk_level: RiskLevel


@dataclass(frozen=True)
class RouteAttempt:
    deployment: str
    status: Literal["succeeded", "failed"]
    latency_ms: int | None
    error: str | None = None


@dataclass(frozen=True)
class GatewayResponse:
    provider: str
    deployment: str
    output_text: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    route: RouteDecision
    attempts: list[RouteAttempt]
