from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .azure_provider import AzureChatProvider
from .config import Settings
from .gateway import Gateway
from .models import ChatMessage, GatewayRequest, RiskLevel, RoutingMode


class ChatMessagePayload(BaseModel):
    role: str
    content: str


class GatewayRequestPayload(BaseModel):
    messages: list[ChatMessagePayload]
    routing_mode: RoutingMode = "balanced"
    risk_level: RiskLevel = "medium"
    requires_json: bool = False
    max_cost_tier: int | None = None
    allowed_deployments: list[str] | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


def create_app() -> FastAPI:
    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )
    app = FastAPI(title="multi-ai-gateway", version="0.2.0")
    app.state.gateway = gateway
    app.state.settings = settings

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "ok": True,
            "deployments": [deployment.name for deployment in settings.default_deployments()],
        }

    @app.post("/v1/complete")
    def complete(request: GatewayRequestPayload) -> dict[str, object]:
        response = gateway.complete(
            GatewayRequest(
                messages=[ChatMessage(role=message.role, content=message.content) for message in request.messages],
                routing_mode=request.routing_mode,
                risk_level=request.risk_level,
                requires_json=request.requires_json,
                max_cost_tier=request.max_cost_tier,
                allowed_deployments=request.allowed_deployments,
                metadata=request.metadata,
            )
        )
        return {
            "provider": response.provider,
            "deployment": response.deployment,
            "output_text": response.output_text,
            "finish_reason": response.finish_reason,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "route": {
                "selected_deployment": response.route.selected_deployment,
                "fallback_chain": response.route.fallback_chain,
                "rationale": response.route.rationale,
                "routing_mode": response.route.routing_mode,
                "risk_level": response.route.risk_level,
            },
            "attempts": [
                {
                    "deployment": attempt.deployment,
                    "status": attempt.status,
                    "latency_ms": attempt.latency_ms,
                    "error": attempt.error,
                }
                for attempt in response.attempts
            ],
        }

    return app


try:
    app = create_app()
except RuntimeError:
    app = FastAPI(title="multi-ai-gateway", version="0.2.0")

    @app.get("/healthz")
    def healthz_unconfigured() -> dict[str, object]:
        return {"ok": False, "error": "azure_gateway_not_configured"}
