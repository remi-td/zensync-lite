"""Sensors for Zendure Local Battery Control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

try:
    from homeassistant.components.sensor import (
        SensorDeviceClass,
        SensorEntity,
        SensorEntityDescription,
        SensorStateClass,
    )
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.const import (
        PERCENTAGE,
        SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        UnitOfElectricCurrent,
        UnitOfElectricPotential,
        UnitOfPower,
        UnitOfTemperature,
        UnitOfTime,
    )
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    from .compat import (  # type: ignore[no-redef]
        PERCENTAGE,
        SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        ConfigEntry,
        EntityCategory,
        HomeAssistant,
        SensorDeviceClass,
        SensorEntity,
        SensorEntityDescription,
        SensorStateClass,
        UnitOfElectricCurrent,
        UnitOfElectricPotential,
        UnitOfPower,
        UnitOfTemperature,
    )
    UnitOfTime = type("UnitOfTime", (), {"MINUTES": "min"})  # type: ignore

from .const import DOMAIN
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity
from .model import ZendureBatteryState

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZendureSensorEntityDescription(SensorEntityDescription):
    """Description for Zendure sensor entity."""

    value_fn: Callable[[ZendureBatteryState], Any] | None = None


CORE_SENSORS: tuple[ZendureSensorEntityDescription, ...] = (
    ZendureSensorEntityDescription(
        key="battery_soc",
        name="Battery SOC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.soc_percent,
    ),
    ZendureSensorEntityDescription(
        key="battery_state",
        name="Battery State",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda s: s.battery_state,
    ),
    ZendureSensorEntityDescription(
        key="solar_input_power",
        name="Solar Input Power",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.solar_input_w,
    ),
    ZendureSensorEntityDescription(
        key="home_output_power",
        name="Home Output Power",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.home_output_w,
    ),
    ZendureSensorEntityDescription(
        key="battery_charge_power",
        name="Battery Charge Power",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.battery_charge_w,
    ),
    ZendureSensorEntityDescription(
        key="battery_discharge_power",
        name="Battery Discharge Power",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.battery_discharge_w,
    ),
    ZendureSensorEntityDescription(
        key="grid_input_power",
        name="Grid Input Power",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.grid_input_w,
    ),
    ZendureSensorEntityDescription(
        key="target_soc",
        name="Target SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.target_soc_percent,
    ),
    ZendureSensorEntityDescription(
        key="minimum_soc",
        name="Minimum SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.min_soc_percent,
    ),
    ZendureSensorEntityDescription(
        key="ac_charge_limit",
        name="AC Charge Limit",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.input_limit_w,
    ),
    ZendureSensorEntityDescription(
        key="output_limit",
        name="Output Limit",
        native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.output_limit_w,
    ),
    ZendureSensorEntityDescription(
        key="device_temperature",
        name="Device Temperature",
        native_unit_of_measurement=getattr(UnitOfTemperature, "CELSIUS", "°C"),
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.temperature_c,
    ),
    ZendureSensorEntityDescription(
        key="rssi",
        name="Signal Strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.rssi_dbm,
    ),
    ZendureSensorEntityDescription(
        key="last_seen",
        name="Last Seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_seen,
    ),
    ZendureSensorEntityDescription(
        key="active_transport",
        name="Active Transport",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.transport,
    ),
    ZendureSensorEntityDescription(
        key="command_status",
        name="Command Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_transaction_state,
    ),
    ZendureSensorEntityDescription(
        key="command_detail",
        name="Command Detail",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_transaction_detail,
    ),
    ZendureSensorEntityDescription(
        key="remaining_discharge_time",
        name="Remaining Discharge Time",
        native_unit_of_measurement=getattr(UnitOfTime, "MINUTES", "min"),
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.remain_out_time_min,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure sensors based on a config entry."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        ZendureSensor(coordinator, desc) for desc in CORE_SENSORS
    ]

    # Optional PV channel sensors (solarPower1 .. solarPower6) - disabled by default
    for i in range(1, 7):
        entities.append(
            ZendurePvChannelSensor(
                coordinator=coordinator,
                channel=i,
                description=ZendureSensorEntityDescription(
                    key=f"solar_power_{i}",
                    name=f"Solar Power PV{i}",
                    native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_registry_enabled_default=False,
                ),
            )
        )

    # Optional per-pack sensors if packData is present
    state = coordinator.current_state
    if state and state.pack_data:
        for idx, pack in enumerate(state.pack_data):
            entities.extend(_build_pack_sensors(coordinator, idx, pack.sn))

    async_add_entities(entities)


def _build_pack_sensors(
    coordinator: ZendureCoordinator,
    pack_idx: int,
    pack_sn: str,
) -> list[SensorEntity]:
    """Build optional disabled-by-default sensors for individual battery packs."""
    pack_label = f"Pack {pack_idx + 1}"
    return [
        ZendurePackSensor(
            coordinator=coordinator,
            pack_idx=pack_idx,
            pack_sn=pack_sn,
            description=ZendureSensorEntityDescription(
                key=f"pack_{pack_sn}_soc",
                name=f"{pack_label} SOC",
                native_unit_of_measurement=PERCENTAGE,
                device_class=SensorDeviceClass.BATTERY,
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=False,
                value_fn=lambda p: p.soc_percent,
            ),
        ),
        ZendurePackSensor(
            coordinator=coordinator,
            pack_idx=pack_idx,
            pack_sn=pack_sn,
            description=ZendureSensorEntityDescription(
                key=f"pack_{pack_sn}_temperature",
                name=f"{pack_label} Temperature",
                native_unit_of_measurement=getattr(UnitOfTemperature, "CELSIUS", "°C"),
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
                value_fn=lambda p: p.max_temp_c,
            ),
        ),
        ZendurePackSensor(
            coordinator=coordinator,
            pack_idx=pack_idx,
            pack_sn=pack_sn,
            description=ZendureSensorEntityDescription(
                key=f"pack_{pack_sn}_power",
                name=f"{pack_label} Power",
                native_unit_of_measurement=getattr(UnitOfPower, "WATT", "W"),
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=False,
                value_fn=lambda p: p.power_w,
            ),
        ),
    ]


class ZendureSensor(ZendureEntity, SensorEntity):
    """Representation of a Zendure sensor."""

    entity_description: ZendureSensorEntityDescription

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        description: ZendureSensorEntityDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.name:
            self._attr_name = description.name

    @property
    def native_value(self) -> Any:
        """Return sensor value derived from confirmed device state."""
        state = self.coordinator.current_state
        if state is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(state)


class ZendurePvChannelSensor(ZendureEntity, SensorEntity):
    """Sensor for individual PV input channel."""

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        channel: int,
        description: ZendureSensorEntityDescription,
    ) -> None:
        """Initialize PV channel sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self.channel = channel
        self._attr_name = description.name

    @property
    def native_value(self) -> int | None:
        """Return power for this channel."""
        state = self.coordinator.current_state
        if state is None:
            return None
        return state.pv_channels_w.get(self.channel)


class ZendurePackSensor(ZendureEntity, SensorEntity):
    """Sensor for a single battery pack."""

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        pack_idx: int,
        pack_sn: str,
        description: ZendureSensorEntityDescription,
    ) -> None:
        """Initialize pack sensor."""
        super().__init__(coordinator, description.key)
        self.pack_idx = pack_idx
        self.pack_sn = pack_sn
        self.entity_description = description
        self._attr_name = description.name

    @property
    def native_value(self) -> Any:
        """Return pack reading."""
        state = self.coordinator.current_state
        if state is None or not state.pack_data:
            return None

        target_pack = None
        for p in state.pack_data:
            if p.sn == self.pack_sn:
                target_pack = p
                break

        if target_pack is None and self.pack_idx < len(state.pack_data):
            target_pack = state.pack_data[self.pack_idx]

        if target_pack is None or self.entity_description.value_fn is None:
            return None

        return self.entity_description.value_fn(target_pack)
