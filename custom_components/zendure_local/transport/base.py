"""Base transport definition for Zendure battery communication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class TransportError(Exception):
    """General transport communication error."""


class TransportTimeoutError(TransportError):
    """Timeout waiting for device response."""


class TransportConnectionError(TransportError):
    """Failed to connect to device endpoint."""


class BaseTransport(ABC):
    """Abstract base class for Zendure communication transports."""

    def __init__(self, serial: str, host: str, port: int) -> None:
        """Initialize base transport."""
        self.serial = serial
        self.host = host
        self.port = port
        self.last_success_time: datetime | None = None
        self.consecutive_failures: int = 0
        self.last_error: str | None = None

    @property
    @abstractmethod
    def transport_type(self) -> str:
        """Return identifier string for the transport (e.g. 'local_http')."""

    @abstractmethod
    async def async_fetch_state(self) -> dict[str, Any]:
        """Fetch current telemetry and property dictionary from device."""

    @abstractmethod
    async def async_write_properties(self, properties: dict[str, Any]) -> bool:
        """Write property modifications to device."""

    @abstractmethod
    async def async_check_health(self) -> bool:
        """Check if transport endpoint is reachable."""

    @abstractmethod
    async def async_close(self) -> None:
        """Close connection pools and clean up resources."""

    def update_endpoint(self, host: str, port: int | None = None) -> None:
        """Update connection endpoint address (e.g. following DHCP IP rediscovery)."""
        self.host = host
        if port is not None:
            self.port = port
