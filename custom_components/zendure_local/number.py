"""Number controls for Zendure Local Battery Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

try:
    from homeassistant.components.number import (
        NumberDeviceClass,
        NumberEntity,
        NumberEntityDescription,
        NumberMode,
    )
    from homeassistant.const import PERCENTAGE, UnitOfPower
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    class NumberEntity:  # type: ignore
        """Mock NumberEntity."""
        _attr_native_value = None

    @dataclass(frozen=True)
    class NumberEntityDescription:  # type: ignore
        """Mock NumberEntityDescription."""
        key: str
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: Any = None
        native_min_value: float = 0
        native_max_value: float = 100
        native_step: float = 1
        mode: Any = "box"

    class NumberDeviceClass:  # type: ignore
        POWER = "power"
        BATTERY = "battery"

    class NumberMode:  # type: ignore
        BOX = "box"
        SLIDER = "slider"

    PERCENTAGE = "%"
    UnitOfPower = type("UnitOfPower", (), {"WATT": "W"})  # type: ignore

from .const import (
    DOMAIN,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SOC_SET,
)
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity
from .model import ZendureBatteryState

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZendureNumberEntityDescription(NumberEntityDescription):
    """Description for Zendure number entity."""

    property_key: str = ""
    value_fn: Callable[[ZendureBatteryState], float | int | None] | None = None
    max_value_fn: Callable[[ZendureCoordinator], float] | None = None


NUMBER_DESCRIPTIONS: tuple[ZendureNumberEntityDescription, ...] = (
    ZendureNumberEntityDescription(
        key="charge_limit_setting",
        name="Charge Limit",
        property_key=PROP_INPUT_LIMIT,
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=NumberDeviceClass.POWER,
        native_min_value=0,
        native_max_value=2400,
        native_step=10,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.input_limit_w,
        max_value_fn=lambda c: float(c.capability.max_charge_w),
    ),
    ZendureNumberEntityDescription(
        key="output_limit_setting",
        name="Output Limit",
        property_key=PROP_OUTPUT_LIMIT,
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=NumberDeviceClass.POWER,
        native_min_value=0,
        native_max_value=2400,
        native_step=10,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.output_limit_w,
        max_value_fn=lambda c: float(c.capability.max_discharge_w),
    ),
    ZendureNumberEntityDescription(
        key="target_soc_setting",
        name="Target SOC Limit",
        property_key=PROP_SOC_SET,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        native_min_value=70,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.target_soc_percent,
    ),
    ZendureNumberEntityDescription(
        key="minimum_soc_setting",
        name="Minimum SOC Limit",
        property_key=PROP_MIN_SOC,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.min_soc_percent,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure number entities."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for desc in NUMBER_DESCRIPTIONS:
        # Check if writable on this device
        if coordinator.capability.can_write(desc.property_key):
            entities.append(ZendureNumber(coordinator, desc))
    async_add_entities(entities)


class ZendureNumber(ZendureEntity, NumberEntity):
    """Representation of a Zendure controllable number."""

    entity_description: ZendureNumberEntityDescription

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        description: ZendureNumberEntityDescription,
    ) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.name:
            self._attr_name = description.name

    @property
    def native_value(self) -> float | None:
        """Return value derived directly from confirmed device truth."""
        state = self.coordinator.current_state
        if state is None or self.entity_description.value_fn is None:
            return None
        val = self.entity_description.value_fn(state)
        return float(val) if val is not None else None

    @property
    def native_max_value(self) -> float:
        """Return dynamic max value based on device capabilities."""
        if self.entity_description.max_value_fn is not None:
            return self.entity_description.max_value_fn(self.coordinator)
        return self.entity_description.native_max_value

    async def async_set_native_value(self, value: float) -> None:
        """Send write request and wait for confirmation."""
        int_val = int(round(value))
        prop_key = self.entity_description.property_key
        _LOGGER.info("Setting %s on %s to %d", prop_key, self.coordinator.serial, int_val)
        success = await self.coordinator.async_execute_write({prop_key: int_val})
        if not success:
            _LOGGER.warning("Failed to confirm setting %s to %d", prop_key, int_val)
