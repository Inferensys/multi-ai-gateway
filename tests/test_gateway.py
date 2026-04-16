from __future__ import annotations

from multi_ai_gateway.config import DeploymentProfile
from multi_ai_gateway.gateway import Gateway, GatewayExecutionError
from multi_ai_gateway.models import ChatMessage, GatewayRequest, RequestContext
from multi_ai_gateway.scenarios import IncidentTriageScenario, ReleaseReviewScenario


class _StubProvider:
    def __init__(self, responses: dict[str, object]):
        self._responses = responses

    def complete(self, *, deployment: str, messages: list[ChatMessage], max_output_tokens: int) -> dict:
        response = self._responses[deployment]
        if isinstance(response, Exception):
            raise response
        return response


def _deployments() -> list[DeploymentProfile]:
    return [
        DeploymentProfile("gpt-5-mini", quality_tier=2, speed_tier=5, cost_tier=1, max_output_tokens=800, notes="fast"),
        DeploymentProfile("gpt-5.4", quality_tier=5, speed_tier=2, cost_tier=3, max_output_tokens=1800, notes="quality"),
    ]


def test_latency_route_prefers_fast_model() -> None:
    gateway = Gateway(
        provider=_StubProvider(
            {
                "gpt-5-mini": {
                    "output_text": "fast",
                    "finish_reason": "stop",
                    "latency_ms": 1100,
                    "prompt_tokens": 12,
                    "completion_tokens": 44,
                    "total_tokens": 56,
                },
                "gpt-5.4": {
                    "output_text": "quality",
                    "finish_reason": "stop",
                    "latency_ms": 3100,
                    "prompt_tokens": 12,
                    "completion_tokens": 44,
                    "total_tokens": 56,
                },
            }
        ),
        deployments=_deployments(),
    )

    response = gateway.complete(
        GatewayRequest(
            messages=[ChatMessage(role="user", content="Summarize this alert.")],
            routing_mode="latency",
            risk_level="low",
            context=RequestContext(
                use_case="incident_triage",
                title="payment-api incident",
                blast_radius="service",
                operator_priority="cost",
                reason_codes=["use_case:incident_triage"],
            ),
        )
    )

    assert response.deployment == "gpt-5-mini"
    assert response.route.selected_deployment == "gpt-5-mini"
    assert response.route.policy_name == "cheap-lane-triage"


def test_quality_route_prefers_heavier_model() -> None:
    gateway = Gateway(
        provider=_StubProvider(
            {
                "gpt-5-mini": {
                    "output_text": "fast",
                    "finish_reason": "stop",
                    "latency_ms": 1100,
                    "prompt_tokens": 12,
                    "completion_tokens": 44,
                    "total_tokens": 56,
                },
                "gpt-5.4": {
                    "output_text": "quality",
                    "finish_reason": "stop",
                    "latency_ms": 3100,
                    "prompt_tokens": 12,
                    "completion_tokens": 44,
                    "total_tokens": 56,
                },
            }
        ),
        deployments=_deployments(),
    )

    response = gateway.complete(
        GatewayRequest(
            messages=[ChatMessage(role="user", content="Assess whether the release should be blocked.")],
            routing_mode="quality",
            risk_level="high",
            context=RequestContext(
                use_case="release_review",
                title="release review",
                blast_radius="money_movement",
                operator_priority="correctness",
                reason_codes=["use_case:release_review", "blast_radius:money_movement"],
            ),
        )
    )

    assert response.deployment == "gpt-5.4"
    assert response.route.selected_deployment == "gpt-5.4"
    assert "blast radius is money_movement" in response.route.why_not_lower_tier


def test_gateway_falls_back_when_primary_fails() -> None:
    gateway = Gateway(
        provider=_StubProvider(
            {
                "gpt-5-mini": RuntimeError("deployment throttled"),
                "gpt-5.4": {
                    "output_text": "quality",
                    "finish_reason": "stop",
                    "latency_ms": 3100,
                    "prompt_tokens": 12,
                    "completion_tokens": 44,
                    "total_tokens": 56,
                },
            }
        ),
        deployments=_deployments(),
    )

    response = gateway.complete(
        GatewayRequest(
            messages=[ChatMessage(role="user", content="Summarize this alert.")],
            routing_mode="latency",
            risk_level="low",
        )
    )

    assert response.deployment == "gpt-5.4"
    assert response.attempts[0].status == "failed"
    assert response.attempts[1].status == "succeeded"


def test_gateway_raises_when_all_attempts_fail() -> None:
    gateway = Gateway(
        provider=_StubProvider(
            {
                "gpt-5-mini": RuntimeError("deployment throttled"),
                "gpt-5.4": RuntimeError("deployment unavailable"),
            }
        ),
        deployments=_deployments(),
    )

    try:
        gateway.complete(
            GatewayRequest(
                messages=[ChatMessage(role="user", content="Summarize this alert.")],
                routing_mode="latency",
                risk_level="low",
            )
        )
    except GatewayExecutionError as exc:
        assert "Last error" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected GatewayExecutionError")


def test_preview_exposes_route_without_execution() -> None:
    gateway = Gateway(
        provider=_StubProvider({}),
        deployments=_deployments(),
    )

    decision = gateway.preview(
        IncidentTriageScenario(
            incident_id="INC-77",
            service="payments-api",
            symptoms=["p95 latency rose above 1.4s"],
            recent_change="cache worker deploy",
            impact_level="low",
        ).to_gateway_request()
    )

    assert decision.selected_deployment == "gpt-5-mini"
    assert decision.policy_name == "cheap-lane-triage"


def test_release_review_scenario_compiles_to_high_blast_radius_request() -> None:
    request = ReleaseReviewScenario(
        release_id="REL-204",
        system_scope="payments checkout",
        change_summary=["moves fraud scoring to async queue"],
        evidence_gaps=["no failover test"],
        historical_failures=["duplicate-capture"],
        timing_pressure="quarter-close",
        blast_radius="money_movement",
    ).to_gateway_request()

    assert request.context.use_case == "release_review"
    assert request.context.blast_radius == "money_movement"
    assert request.routing_mode == "quality"
    assert request.risk_level == "high"
