from __future__ import annotations

from .config import DeploymentProfile
from .models import GatewayRequest, GatewayResponse, RouteAttempt
from .router import Router


class GatewayExecutionError(RuntimeError):
    pass


class Gateway:
    def __init__(self, provider: object, deployments: list[DeploymentProfile], router: Router | None = None) -> None:
        self._provider = provider
        self._deployments = deployments
        self._router = router or Router()

    def complete(self, request: GatewayRequest) -> GatewayResponse:
        decision = self._router.choose(request, self._deployments)
        attempt_names = [decision.selected_deployment, *decision.fallback_chain]
        deployment_index = {deployment.name: deployment for deployment in self._deployments}
        attempts: list[RouteAttempt] = []
        last_error: str | None = None

        for deployment_name in attempt_names:
            deployment = deployment_index[deployment_name]
            try:
                result = self._provider.complete(
                    deployment=deployment.name,
                    messages=request.messages,
                    max_output_tokens=deployment.max_output_tokens,
                )
            except Exception as exc:
                last_error = str(exc)
                attempts.append(
                    RouteAttempt(
                        deployment=deployment.name,
                        status="failed",
                        latency_ms=None,
                        error=str(exc),
                    )
                )
                continue

            attempts.append(
                RouteAttempt(
                    deployment=deployment.name,
                    status="succeeded",
                    latency_ms=result["latency_ms"],
                )
            )
            return GatewayResponse(
                provider="azure-openai",
                deployment=deployment.name,
                output_text=result["output_text"],
                finish_reason=result["finish_reason"],
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                route=decision,
                attempts=attempts,
            )

        raise GatewayExecutionError(
            "All route attempts failed."
            + (f" Last error: {last_error}" if last_error else "")
        )
