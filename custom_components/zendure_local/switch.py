"""Switch controls for Zendure Local Battery Control."""

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    class SwitchEntity:  # type: ignore
        """Mock SwitchEntity."""
        _attr_is_on = None

    class SwitchDeviceClass:  # type: ignore
        SWITCH = "switch"

    class EntityCategory:  # type: ignore
        CONFIG = "config"

from .const import DOMAIN, PROP_GRID_REVERSE, PROP_SMART_MODE
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure switches."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []

    if coordinator.capability.can_write(PROP_SMART_MODE):
        entities.append(ZendureSmartModeSwitch(coordinator))

    if coordinator.capability.can_write(PROP_GRID_REVERSE):
        entities.append(ZendureGridReverseSwitch(coordinator))

    async_add_entities(entities)


class ZendureSmartModeSwitch(ZendureEntity, SwitchEntity):
    """Switch for enabling volatile / frequent-write mode (smartMode: 1).
    
    When enabled, commands do not write to non-volatile flash, preventing NAND wear
    during frequent automation adjustments (e.g. solar surplus regulation).
    """

    def __init__(self, coordinator: ZendureCoordinator) -> None:
        """Initialize switch."""
        super().__init__(coordinator, "smart_mode")
        self._attr_name = "Volatile Write Mode"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool | None:
        """Return True if smartMode is active (volatile mode enabled)."""
        state = self.coordinator.current_state
        if state is None:
            return None
        if state.smart_mode is not None:
            return state.smart_mode == 1
        return self.coordinator.volatile_writes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable volatile memory writes."""
        self.coordinator.volatile_writes = True
        _LOGGER.info("Enabling volatile write mode on %s", self.coordinator.serial)
        await self.coordinator.async_execute_write({PROP_SMART_MODE: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable volatile memory writes (commits to flash)."""
        self.coordinator.volatile_writes = False
        _LOGGER.info("Disabling volatile write mode on %s", self.coordinator.serial)
        await self.coordinator.async_execute_write({PROP_SMART_MODE: 0})


class ZendureGridReverseSwitch(ZendureEntity, SwitchEntity):
    """Switch for reverse flow control."""

    def __init__(self, coordinator: ZendureCoordinator) -> None:
        """Initialize switch."""
        super().__init__(coordinator, "grid_reverse")
        self._attr_name = "Grid Reverse Flow"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool | None:
        """Return True if reverse flow is permitted."""
        state = self.coordinator.current_state
        if state is None or state.grid_reverse is None:
            return None
        return state.grid_reverse > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable grid reverse flow."""
        await self.coordinator.async_execute_write({PROP_GRID_REVERSE: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable grid reverse flow."""
        await self.coordinator.async_execute_write({PROP_GRID_REVERSE: 0})
