"""Optional Cloud fallback transport for Zendure devices."""

from __future__ import annotations

import logging
from typing import Any

from ..const import TRANSPORT_CLOUD
from .base import BaseTransport, TransportError

_LOGGER = logging.getLogger(__name__)


class CloudTransport(BaseTransport):
    """Fallback transport for initial discovery or emergency cloud operation."""

    def __init__(self, serial: str, app_key: str = "", app_secret: str = "") -> None:
        """Initialize CloudTransport."""
        super().__init__(serial=serial, host="cloud.zendure.com", port=443)
        self.app_key = app_key
        self.app_secret = app_secret
        self.enabled: bool = False

    @property
    def transport_type(self) -> str:
        """Return identifier."""
        return TRANSPORT_CLOUD

    async def async_fetch_state(self) -> dict[str, Any]:
        """Cloud state fetch."""
        if not self.enabled:
            raise TransportError("Cloud transport is disabled by default")
        raise NotImplementedError("Cloud fallback is not enabled for this device")

    async def async_write_properties(self, properties: dict[str, Any]) -> bool:
        """Cloud property write."""
        if not self.enabled:
            raise TransportError("Cloud transport is disabled by default")
        raise NotImplementedError("Cloud fallback is not enabled for this device")

    async def async_check_health(self) -> bool:
        """Check cloud API accessibility."""
        return False

    async def async_close(self) -> None:
        """Close cloud connections."""
        pass
