"""Base entity class for Zendure Local Battery Control."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

try:
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.update_coordinator import CoordinatorEntity
except ImportError:
    from .compat import CoordinatorEntity, DeviceInfo  # type: ignore[no-redef]

from .const import DOMAIN, MANUFACTURER
from .coordinator import ZendureCoordinator


class ZendureEntity(CoordinatorEntity[ZendureCoordinator]):
    """Base class for Zendure entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        key: str,
    ) -> None:
        """Initialize Zendure entity."""
        super().__init__(coordinator)
        self._key = key
        # Unique ID must include serial number to prevent duplicate collisions
        self._attr_unique_id = f"zensync_lite_{coordinator.serial}_{key}"

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return self._attr_unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the Zendure device."""
        state = self.coordinator.current_state
        sw_ver = None
        if state and state.firmware:
            sw_ver = str(state.firmware.get("version") or "")

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial)},
            name=f"Zendure {self.coordinator.model} ({self.coordinator.serial})",
            manufacturer=MANUFACTURER,
            model=self.coordinator.model,
            sw_version=sw_ver,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available and state is fresh."""
        if not self.coordinator.last_update_success:
            return False
        state = self.coordinator.current_state
        if state is None:
            return False
        return state.available and not state.stale
