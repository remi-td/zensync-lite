"""Select controls for Zendure Local Battery Control."""

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.components.select import SelectEntity, SelectEntityDescription
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    from .compat import HomeAssistant, SelectEntity, SelectEntityDescription  # type: ignore[no-redef]

from .const import (
    DOMAIN,
    MAP_AC_MODE_TO_STR,
    MAP_STR_TO_AC_MODE,
    MODE_CHARGE_STR,
    MODE_DISCHARGE_STR,
    PROP_AC_MODE,
)
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure select entities."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if coordinator.capability.can_write(PROP_AC_MODE):
        async_add_entities([ZendureModeSelect(coordinator)])


class ZendureModeSelect(ZendureEntity, SelectEntity):
    """Select entity for controlling Zendure AC inverter mode (Charge/Discharge)."""

    def __init__(self, coordinator: ZendureCoordinator) -> None:
        """Initialize mode select entity."""
        super().__init__(coordinator, "ac_mode")
        self._attr_name = "Operating Mode"
        self._attr_options = [MODE_CHARGE_STR, MODE_DISCHARGE_STR]

    @property
    def current_option(self) -> str | None:
        """Return the confirmed active mode from device."""
        state = self.coordinator.current_state
        if state is None or state.ac_mode is None:
            return None
        return MAP_AC_MODE_TO_STR.get(state.ac_mode)

    async def async_select_option(self, option: str) -> None:
        """Change operating mode on device and wait for readback confirmation."""
        raw_val = MAP_STR_TO_AC_MODE.get(option)
        if raw_val is None:
            _LOGGER.error("Invalid operating mode requested: %s", option)
            return

        _LOGGER.info("Setting operating mode on %s to %s (%d)", self.coordinator.serial, option, raw_val)
        success = await self.coordinator.async_execute_write({PROP_AC_MODE: raw_val})
        if not success:
            _LOGGER.warning("Failed to confirm setting operating mode to %s", option)
