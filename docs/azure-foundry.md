# Azure Foundry

This repo routes between Azure deployments, not between marketing labels.

The current default inventory is:

- `gpt-5-mini`: fast lane
- `gpt-5.4`: quality lane

The router is deterministic and app-owned. Azure is only used for execution after the route is chosen.

## Environment

```bash
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_API_VERSION="2025-04-01-preview"
export MULTI_AI_GATEWAY_FAST_DEPLOYMENT="gpt-5-mini"
export MULTI_AI_GATEWAY_QUALITY_DEPLOYMENT="gpt-5.4"
```

Run the live demo:

```bash
uv run python scripts/run_live_demo.py
```

Start the API:

```bash
uv run uvicorn multi_ai_gateway.main:app --app-dir src --reload
```

## Portability Notes

To add OpenAI, Vertex, Anthropic, or Bedrock later:

- keep `Router` untouched
- implement a provider with the `complete(deployment, messages, max_output_tokens)` contract
- reuse the same `DeploymentProfile` metadata so route behavior stays explainable

Do not push route choice into the provider. Once a provider decides the route, you lose auditability.
