from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .models import ChatMessage, GatewayRequest, RequestContext


@dataclass(frozen=True)
class IncidentTriageScenario:
    incident_id: str
    service: str
    symptoms: list[str]
    recent_change: str | None = None
    impact_level: Literal["low", "medium", "high"] = "low"
    response_style: str = "Respond in 5 concise bullets max."

    def to_gateway_request(self) -> GatewayRequest:
        symptom_block = "\n".join(f"- {item}" for item in self.symptoms)
        recent_change = self.recent_change or "No recent change was provided."
        return GatewayRequest(
            messages=[
                ChatMessage(
                    role="system",
                    content=f"You are an incident triage assistant. {self.response_style}",
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"Incident: {self.incident_id}\n"
                        f"Service: {self.service}\n"
                        f"Impact: {self.impact_level}\n"
                        "Observed symptoms:\n"
                        f"{symptom_block}\n\n"
                        f"Recent change: {recent_change}"
                    ),
                ),
            ],
            routing_mode="latency",
            risk_level="medium" if self.impact_level == "high" else self.impact_level,
            max_cost_tier=1 if self.impact_level != "high" else 2,
            metadata={"scenario": "incident-triage", "service": self.service},
            context=RequestContext(
                use_case="incident_triage",
                title=f"{self.service} incident triage",
                summary=f"{self.incident_id} triage for {self.service}",
                blast_radius="service",
                operator_priority="cost",
                reason_codes=[
                    "use_case:incident_triage",
                    f"service:{self.service}",
                    f"impact:{self.impact_level}",
                ],
            ),
        )


@dataclass(frozen=True)
class ReleaseReviewScenario:
    release_id: str
    system_scope: str
    change_summary: list[str]
    evidence_gaps: list[str] = field(default_factory=list)
    historical_failures: list[str] = field(default_factory=list)
    timing_pressure: str | None = None
    blast_radius: Literal["service", "cross_service", "money_movement"] = "cross_service"

    def to_gateway_request(self) -> GatewayRequest:
        change_block = "\n".join(f"- {item}" for item in self.change_summary)
        evidence_block = "\n".join(f"- {item}" for item in self.evidence_gaps) or "- none listed"
        history_block = "\n".join(f"- {item}" for item in self.historical_failures) or "- none listed"
        timing_line = self.timing_pressure or "No explicit launch pressure was provided."
        return GatewayRequest(
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "You are a release review assistant. Give a direct ship or hold recommendation, "
                        "then justify it with operational risks and a short mitigation plan."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        f"Release: {self.release_id}\n"
                        f"System scope: {self.system_scope}\n"
                        "Change summary:\n"
                        f"{change_block}\n\n"
                        "Evidence gaps:\n"
                        f"{evidence_block}\n\n"
                        "Relevant historical failures:\n"
                        f"{history_block}\n\n"
                        f"Launch pressure: {timing_line}"
                    ),
                ),
            ],
            routing_mode="quality",
            risk_level="high",
            metadata={"scenario": "release-review", "release_id": self.release_id},
            context=RequestContext(
                use_case="release_review",
                title=f"{self.release_id} release review",
                summary=f"Release review for {self.system_scope}",
                blast_radius=self.blast_radius,
                operator_priority="correctness",
                reason_codes=[
                    "use_case:release_review",
                    f"blast_radius:{self.blast_radius}",
                    *(f"history:{item}" for item in self.historical_failures),
                    *(f"gap:{item}" for item in self.evidence_gaps),
                    *( [f"pressure:{self.timing_pressure}"] if self.timing_pressure else [] ),
                ],
            ),
        )


def request_from_payload(payload: dict[str, Any]) -> GatewayRequest:
    kind = payload.get("kind")
    if kind == "incident_triage":
        scenario = IncidentTriageScenario(
            incident_id=str(payload["incident_id"]),
            service=str(payload["service"]),
            symptoms=[str(item) for item in payload["symptoms"]],
            recent_change=_optional_str(payload.get("recent_change")),
            impact_level=str(payload.get("impact_level", "low")),  # type: ignore[arg-type]
            response_style=str(payload.get("response_style", "Respond in 5 concise bullets max.")),
        )
        return scenario.to_gateway_request()

    if kind == "release_review":
        scenario = ReleaseReviewScenario(
            release_id=str(payload["release_id"]),
            system_scope=str(payload["system_scope"]),
            change_summary=[str(item) for item in payload["change_summary"]],
            evidence_gaps=[str(item) for item in payload.get("evidence_gaps", [])],
            historical_failures=[str(item) for item in payload.get("historical_failures", [])],
            timing_pressure=_optional_str(payload.get("timing_pressure")),
            blast_radius=str(payload.get("blast_radius", "cross_service")),  # type: ignore[arg-type]
        )
        return scenario.to_gateway_request()

    return GatewayRequest(
        messages=[ChatMessage(role=item["role"], content=item["content"]) for item in payload["messages"]],
        routing_mode=payload.get("routing_mode", "balanced"),
        risk_level=payload.get("risk_level", "medium"),
        requires_json=payload.get("requires_json", False),
        max_cost_tier=payload.get("max_cost_tier"),
        allowed_deployments=payload.get("allowed_deployments"),
        metadata=payload.get("metadata", {}),
        context=RequestContext(
            use_case=payload.get("use_case", "generic"),
            title=payload.get("title", ""),
            summary=payload.get("summary", ""),
            blast_radius=payload.get("blast_radius", "service"),
            operator_priority=payload.get("operator_priority", "balanced"),
            reason_codes=[str(item) for item in payload.get("reason_codes", [])],
        ),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
