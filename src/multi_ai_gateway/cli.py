from __future__ import annotations

import argparse
import json
from pathlib import Path

from .azure_provider import AzureChatProvider
from .config import Settings
from .gateway import Gateway
from .models import ChatMessage, GatewayRequest


def main() -> None:
    parser = argparse.ArgumentParser(prog="mag")
    subparsers = parser.add_subparsers(dest="command", required=True)

    complete = subparsers.add_parser("complete", help="Route a request through the gateway.")
    complete.add_argument("--input-file", required=True)
    complete.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.command == "complete":
        _run_complete(args)


def _run_complete(args: argparse.Namespace) -> None:
    request_payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )
    request = GatewayRequest(
        messages=[ChatMessage(role=item["role"], content=item["content"]) for item in request_payload["messages"]],
        routing_mode=request_payload.get("routing_mode", "balanced"),
        risk_level=request_payload.get("risk_level", "medium"),
        requires_json=request_payload.get("requires_json", False),
        max_cost_tier=request_payload.get("max_cost_tier"),
        allowed_deployments=request_payload.get("allowed_deployments"),
        metadata=request_payload.get("metadata", {}),
    )
    response = gateway.complete(request)
    Path(args.out).write_text(
        json.dumps(
            {
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
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
