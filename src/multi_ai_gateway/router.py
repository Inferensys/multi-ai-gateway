from __future__ import annotations

from .config import DeploymentProfile
from .models import GatewayRequest, RouteDecision


class Router:
    def choose(self, request: GatewayRequest, deployments: list[DeploymentProfile]) -> RouteDecision:
        candidates = deployments
        if request.allowed_deployments:
            allowed = set(request.allowed_deployments)
            candidates = [deployment for deployment in candidates if deployment.name in allowed]
        if request.max_cost_tier is not None:
            candidates = [
                deployment
                for deployment in candidates
                if deployment.cost_tier <= request.max_cost_tier
            ]
        if not candidates:
            raise RuntimeError("No deployment candidates remain after applying route constraints.")

        ranked = sorted(
            candidates,
            key=lambda deployment: self._score(request, deployment),
        )
        selected = ranked[0]
        fallback_chain = [deployment.name for deployment in ranked[1:]]
        return RouteDecision(
            selected_deployment=selected.name,
            fallback_chain=fallback_chain,
            rationale=self._rationale(request, selected),
            routing_mode=request.routing_mode,
            risk_level=request.risk_level,
        )

    def _score(self, request: GatewayRequest, deployment: DeploymentProfile) -> tuple[int, int, int]:
        quality_gap = max(0, _required_quality(request) - deployment.quality_tier)
        if request.routing_mode == "latency":
            return (quality_gap * 100, -deployment.speed_tier, deployment.cost_tier)
        if request.routing_mode == "quality":
            return (quality_gap * 100, -deployment.quality_tier, deployment.cost_tier)
        return (
            quality_gap * 100,
            abs(deployment.quality_tier - _balanced_quality_target(request)),
            abs(deployment.speed_tier - 3),
        )

    def _rationale(self, request: GatewayRequest, selected: DeploymentProfile) -> str:
        reasons: list[str] = [f"routing_mode={request.routing_mode}", f"risk_level={request.risk_level}"]
        if request.requires_json:
            reasons.append("json_contract=true")
        if request.max_cost_tier is not None:
            reasons.append(f"max_cost_tier={request.max_cost_tier}")
        reasons.append(
            "selected="
            f"{selected.name}(quality={selected.quality_tier},speed={selected.speed_tier},cost={selected.cost_tier})"
        )
        return ", ".join(reasons)


def _required_quality(request: GatewayRequest) -> int:
    risk_target = {"low": 1, "medium": 3, "high": 5}[request.risk_level]
    if request.routing_mode == "quality":
        risk_target = max(risk_target, 4)
    if request.requires_json:
        risk_target = max(risk_target, 3)
    return risk_target


def _balanced_quality_target(request: GatewayRequest) -> int:
    return max(2, _required_quality(request))
