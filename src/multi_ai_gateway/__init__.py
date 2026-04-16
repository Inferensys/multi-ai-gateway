"""Deterministic model routing with provider-swappable execution backends."""

from typing import Any

from .config import DeploymentProfile, Settings
from .gateway import Gateway, GatewayExecutionError
from .models import (
    ChatMessage,
    GatewayRequest,
    GatewayResponse,
    RouteAttempt,
    RouteDecision,
    RoutingMode,
)
from .router import Router

__version__ = "0.2.0"

__all__ = [
    "ChatMessage",
    "DeploymentProfile",
    "Gateway",
    "GatewayExecutionError",
    "GatewayRequest",
    "GatewayResponse",
    "RouteAttempt",
    "RouteDecision",
    "Router",
    "RoutingMode",
    "Settings",
]


def __getattr__(name: str) -> Any:
    if name == "AzureChatProvider":
        from .azure_provider import AzureChatProvider

        return AzureChatProvider
    raise AttributeError(name)
