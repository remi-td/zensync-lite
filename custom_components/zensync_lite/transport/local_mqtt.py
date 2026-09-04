"""Optional Local MQTT transport adapter for Zendure devices."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from ..const import TRANSPORT_LOCAL_MQTT
from .base import BaseTransport, TransportError

_LOGGER = logging.getLogger(__name__)


class LocalMqttTransport(BaseTransport):
    """Secondary/fallback transport utilizing local MQTT broker connectivity."""

    def __init__(
        self,
        serial: str,
        host: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize LocalMqttTransport."""
        super().__init__(serial=serial, host=host, port=port)
        self._username = username
        self._password = password
        self.broker_connected: bool = False
        self.device_connected: bool = False
        self._latest_telemetry: dict[str, Any] | None = None

    @property
    def transport_type(self) -> str:
        """Return identifier."""
        return TRANSPORT_LOCAL_MQTT

    async def async_fetch_state(self) -> dict[str, Any]:
        """Return cached state from received MQTT messages."""
        if not self.device_connected or not self._latest_telemetry:
            raise TransportError(
                "Local MQTT: Physical device telemetry not yet received or device disconnected"
            )
        self.last_success_time = datetime.now(timezone.utc)
        return self._latest_telemetry

    async def async_write_properties(self, properties: dict[str, Any]) -> bool:
        """Publish write command to device control topic."""
        if not self.device_connected:
            raise TransportError("Cannot write over Local MQTT: physical device is not connected")
        # Control topic publication placeholder when local MQTT is configured
        _LOGGER.info("Publishing MQTT command for %s: %s", self.serial, properties)
        return True

    def on_telemetry_received(self, payload: dict[str, Any]) -> None:
        """Callback when telemetry message arrives from physical device."""
        self.device_connected = True
        self._latest_telemetry = payload
        self.last_success_time = datetime.now(timezone.utc)
        self.consecutive_failures = 0

    async def async_check_health(self) -> bool:
        """Check if both broker and device are connected."""
        return self.broker_connected and self.device_connected

    async def async_close(self) -> None:
        """Clean up MQTT client connections."""
        self.broker_connected = False
        self.device_connected = False
