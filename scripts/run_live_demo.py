from __future__ import annotations

import json
from pathlib import Path

from multi_ai_gateway import ChatMessage, Gateway, GatewayRequest, Settings
from multi_ai_gateway.azure_provider import AzureChatProvider


ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "demo" / "input"
OUTPUT_DIR = ROOT / "demo" / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    settings = Settings.from_env()
    gateway = Gateway(
        provider=AzureChatProvider(settings),
        deployments=settings.default_deployments(),
    )

    scenarios = [
        ("fast-triage", "fast-triage.json"),
        ("release-risk", "release-risk.json"),
    ]

    summary: list[dict[str, object]] = []
    for name, filename in scenarios:
        print(f"[{name}] routing request")
        payload = json.loads((INPUT_DIR / filename).read_text(encoding="utf-8"))
        request = GatewayRequest(
            messages=[ChatMessage(role=item["role"], content=item["content"]) for item in payload["messages"]],
            routing_mode=payload.get("routing_mode", "balanced"),
            risk_level=payload.get("risk_level", "medium"),
            requires_json=payload.get("requires_json", False),
            max_cost_tier=payload.get("max_cost_tier"),
            allowed_deployments=payload.get("allowed_deployments"),
            metadata=payload.get("metadata", {}),
        )
        response = gateway.complete(request)
        artifact = {
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
        _write_json(OUTPUT_DIR / f"{name}.json", artifact)
        summary.append(
            {
                "name": name,
                "deployment": response.deployment,
                "latency_ms": response.attempts[-1].latency_ms,
                "total_tokens": response.total_tokens,
                "fallbacks_used": len([attempt for attempt in response.attempts if attempt.status == "failed"]),
            }
        )
        print(
            f"[{name}] deployment={response.deployment} "
            f"latency_ms={response.attempts[-1].latency_ms} total_tokens={response.total_tokens}"
        )

    _write_json(OUTPUT_DIR / "demo-summary.json", summary)
    print(f"wrote demo artifacts to {OUTPUT_DIR}")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
