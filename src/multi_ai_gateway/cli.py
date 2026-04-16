from __future__ import annotations

import argparse
import json
from pathlib import Path

from .azure_provider import AzureChatProvider
from .config import Settings
from .gateway import Gateway
from .scenarios import request_from_payload


def main() -> None:
    parser = argparse.ArgumentParser(prog="mag")
    subparsers = parser.add_subparsers(dest="command", required=True)

    complete = subparsers.add_parser("complete", help="Route a request through the gateway.")
    complete.add_argument("--input-file", required=True)
    complete.add_argument("--out", required=True)

    preview = subparsers.add_parser("preview", help="Preview the selected deployment without executing.")
    preview.add_argument("--input-file", required=True)
    preview.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.command == "complete":
        _run_complete(args)
    if args.command == "preview":
        _run_preview(args)


def _run_complete(args: argparse.Namespace) -> None:
    request_payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )
    request = request_from_payload(request_payload)
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
                    "policy_name": response.route.policy_name,
                    "reason_codes": response.route.reason_codes,
                    "why_not_lower_tier": response.route.why_not_lower_tier,
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


def _run_preview(args: argparse.Namespace) -> None:
    request_payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )
    request = request_from_payload(request_payload)
    decision = gateway.preview(request)
    Path(args.out).write_text(
        json.dumps(
            {
                "selected_deployment": decision.selected_deployment,
                "fallback_chain": decision.fallback_chain,
                "rationale": decision.rationale,
                "routing_mode": decision.routing_mode,
                "risk_level": decision.risk_level,
                "policy_name": decision.policy_name,
                "reason_codes": decision.reason_codes,
                "why_not_lower_tier": decision.why_not_lower_tier,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
