"""Deterministic model routing with provider-swappable execution backends."""

from typing import Any

from .config import DeploymentProfile, Settings
from .gateway import Gateway, GatewayExecutionError
from .models import (
    ChatMessage,
    GatewayRequest,
    GatewayResponse,
    RequestContext,
    RouteAttempt,
    RouteDecision,
    RoutingMode,
)
from .scenarios import IncidentTriageScenario, ReleaseReviewScenario, request_from_payload
from .router import Router

__version__ = "0.3.0"

__all__ = [
    "ChatMessage",
    "DeploymentProfile",
    "Gateway",
    "GatewayExecutionError",
    "GatewayRequest",
    "GatewayResponse",
    "IncidentTriageScenario",
    "ReleaseReviewScenario",
    "RequestContext",
    "RouteAttempt",
    "RouteDecision",
    "Router",
    "RoutingMode",
    "Settings",
    "request_from_payload",
]


def __getattr__(name: str) -> Any:
    if name == "AzureChatProvider":
        from .azure_provider import AzureChatProvider

        return AzureChatProvider
    raise AttributeError(name)
