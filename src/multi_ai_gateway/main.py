from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .azure_provider import AzureChatProvider
from .config import Settings
from .gateway import Gateway
from .models import ChatMessage, GatewayRequest, RiskLevel, RoutingMode
from .scenarios import IncidentTriageScenario, ReleaseReviewScenario, request_from_payload


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


class IncidentTriagePayload(BaseModel):
    incident_id: str
    service: str
    symptoms: list[str]
    recent_change: str | None = None
    impact_level: RiskLevel = "low"
    response_style: str = "Respond in 5 concise bullets max."


class ReleaseReviewPayload(BaseModel):
    release_id: str
    system_scope: str
    change_summary: list[str]
    evidence_gaps: list[str] = Field(default_factory=list)
    historical_failures: list[str] = Field(default_factory=list)
    timing_pressure: str | None = None
    blast_radius: str = "cross_service"


def _serialize_route(route) -> dict[str, object]:
    return {
        "selected_deployment": route.selected_deployment,
        "fallback_chain": route.fallback_chain,
        "rationale": route.rationale,
        "routing_mode": route.routing_mode,
        "risk_level": route.risk_level,
        "policy_name": route.policy_name,
        "reason_codes": route.reason_codes,
        "why_not_lower_tier": route.why_not_lower_tier,
    }


def _serialize_response(response) -> dict[str, object]:
    return {
        "provider": response.provider,
        "deployment": response.deployment,
        "output_text": response.output_text,
        "finish_reason": response.finish_reason,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "total_tokens": response.total_tokens,
        "route": _serialize_route(response.route),
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


def create_app() -> FastAPI:
    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )
    app = FastAPI(title="multi-ai-gateway", version="0.3.0")
    app.state.gateway = gateway
    app.state.settings = settings

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {
            "ok": True,
            "deployments": [deployment.name for deployment in settings.default_deployments()],
            "scenario_endpoints": ["incident-triage", "release-review"],
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
        return _serialize_response(response)

    @app.post("/v1/route-preview")
    def route_preview(payload: dict[str, Any]) -> dict[str, object]:
        request = request_from_payload(payload)
        return _serialize_route(gateway.preview(request))

    @app.post("/v1/scenarios/incident-triage")
    def incident_triage(payload: IncidentTriagePayload) -> dict[str, object]:
        request = IncidentTriageScenario(**payload.model_dump()).to_gateway_request()
        return _serialize_response(gateway.complete(request))

    @app.post("/v1/scenarios/release-review")
    def release_review(payload: ReleaseReviewPayload) -> dict[str, object]:
        request = ReleaseReviewScenario(**payload.model_dump()).to_gateway_request()
        return _serialize_response(gateway.complete(request))

    return app


try:
    app = create_app()
except RuntimeError:
    app = FastAPI(title="multi-ai-gateway", version="0.3.0")

    @app.get("/healthz")
    def healthz_unconfigured() -> dict[str, object]:
        return {"ok": False, "error": "azure_gateway_not_configured"}
