"""Binary sensors for Zendure Local Battery Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

try:
    from homeassistant.components.binary_sensor import (
        BinarySensorDeviceClass,
        BinarySensorEntity,
        BinarySensorEntityDescription,
    )
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    class BinarySensorEntity:  # type: ignore
        """Mock BinarySensorEntity."""
        _attr_is_on = None

    @dataclass(frozen=True)
    class BinarySensorEntityDescription:  # type: ignore
        """Mock BinarySensorEntityDescription."""
        key: str
        name: str | None = None
        device_class: Any = None
        entity_category: Any = None
        entity_registry_enabled_default: bool = True

    class BinarySensorDeviceClass:  # type: ignore
        CONNECTIVITY = "connectivity"
        PROBLEM = "problem"
        HEAT = "heat"
        RUNNING = "running"

    class EntityCategory:  # type: ignore
        DIAGNOSTIC = "diagnostic"

from .const import DOMAIN, TRANSPORT_LOCAL_HTTP
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity
from .model import ZendureBatteryState

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZendureBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for Zendure binary sensor entity."""

    is_on_fn: Callable[[ZendureBatteryState], bool | None] | None = None


BINARY_SENSORS: tuple[ZendureBinarySensorEntityDescription, ...] = (
    ZendureBinarySensorEntityDescription(
        key="available",
        name="Device Available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s.available and not s.stale,
    ),
    ZendureBinarySensorEntityDescription(
        key="stale_data",
        name="Data Stale",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s.stale,
    ),
    ZendureBinarySensorEntityDescription(
        key="error_present",
        name="Error Present",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: bool(s.error) or (s.fault_level is not None and s.fault_level > 0),
    ),
    ZendureBinarySensorEntityDescription(
        key="grid_connected",
        name="Grid Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda s: s.grid_connected,
    ),
    ZendureBinarySensorEntityDescription(
        key="reverse_flow_active",
        name="Reverse Flow Active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s.reverse_flow_active,
    ),
    ZendureBinarySensorEntityDescription(
        key="local_api_available",
        name="Local API Available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s.transport == TRANSPORT_LOCAL_HTTP and s.available,
    ),
    ZendureBinarySensorEntityDescription(
        key="heating_active",
        name="Heating Active",
        device_class=BinarySensorDeviceClass.HEAT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda s: s.heating,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure binary sensors."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [ZendureBinarySensor(coordinator, desc) for desc in BINARY_SENSORS]
    async_add_entities(entities)


class ZendureBinarySensor(ZendureEntity, BinarySensorEntity):
    """Representation of a Zendure binary sensor."""

    entity_description: ZendureBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        description: ZendureBinarySensorEntityDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.name:
            self._attr_name = description.name

    @property
    def is_on(self) -> bool | None:
        """Return True if binary sensor is on."""
        state = self.coordinator.current_state
        if state is None or self.entity_description.is_on_fn is None:
            return None
        return self.entity_description.is_on_fn(state)
