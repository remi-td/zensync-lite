"""Compatibility and fallback mocks for running unit tests without Home Assistant Core.

When running inside Home Assistant, native Home Assistant imports are used directly.
This module is only invoked when `import homeassistant` raises ImportError.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")

# Core mocks
class HomeAssistant:
    """Mock HomeAssistant instance."""

    def __init__(self, config_dir: str = "/config") -> None:
        self.config_dir = config_dir
        self.data: dict[str, Any] = {}
        self.loop = asyncio.get_event_loop()
        self.bus = MockBus()
        self.services = MockServices()

    def async_create_task(self, target: Any) -> asyncio.Task:
        return self.loop.create_task(target)


class MockBus:
    def async_fire(self, event_type: str, event_data: dict[str, Any] | None = None) -> None:
        pass


class MockServices:
    def __init__(self) -> None:
        self._services: dict[str, dict[str, Callable]] = {}

    def async_register(
        self, domain: str, service: str, handler: Callable, schema: Any = None
    ) -> None:
        self._services.setdefault(domain, {})[service] = handler

    def async_remove(self, domain: str, service: str) -> None:
        self._services.get(domain, {}).pop(service, None)


def callback(func: _T) -> _T:
    return func


class ConfigEntry:
    """Mock ConfigEntry."""

    def __init__(
        self,
        entry_id: str = "mock_entry_id",
        domain: str = "zensync_lite",
        title: str = "Mock Zendure",
        data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        unique_id: str | None = None,
    ) -> None:
        self.entry_id = entry_id
        self.domain = domain
        self.title = title
        self.data = data or {}
        self.options = options or {}
        self.unique_id = unique_id

    def add_update_listener(self, listener: Callable) -> Callable:
        return lambda: None

    def async_on_unload(self, callback_fn: Callable) -> None:
        pass


class ConfigFlowResult(dict):
    """Mock ConfigFlowResult."""
    pass


FlowResult = ConfigFlowResult


class config_entries:
    class ConfigFlow:
        def __init_subclass__(cls, domain: str = "", **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        def __init__(self) -> None:
            self.context: dict[str, Any] = {}
            self._unique_id: str | None = None

        async def async_set_unique_id(self, unique_id: str) -> None:
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self, updates: dict[str, Any] | None = None) -> None:
            pass

        def async_show_form(self, **kwargs: Any) -> ConfigFlowResult:
            return ConfigFlowResult({"type": "form", **kwargs})

        def async_create_entry(self, **kwargs: Any) -> ConfigFlowResult:
            return ConfigFlowResult({"type": "create_entry", **kwargs})

        def async_abort(self, **kwargs: Any) -> ConfigFlowResult:
            return ConfigFlowResult({"type": "abort", **kwargs})

    class OptionsFlow:
        def __init__(self, config_entry: Any = None) -> None:
            self.config_entry = config_entry

        def async_show_form(self, **kwargs: Any) -> ConfigFlowResult:
            return ConfigFlowResult({"type": "form", **kwargs})

        def async_create_entry(self, **kwargs: Any) -> ConfigFlowResult:
            return ConfigFlowResult({"type": "create_entry", **kwargs})


class ZeroconfServiceInfo:
    host: str = ""
    port: int | None = None
    name: str = ""


# Coordinator mocks
class DataUpdateCoordinator(Generic[_T]):
    """Mock DataUpdateCoordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Any,
        name: str,
        update_interval: timedelta | None = None,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: _T | None = None
        self.last_update_success: bool = True
        self._listeners: list[Callable[[], None]] = []

    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback)

    def async_update_listeners(self) -> None:
        for listener in self._listeners:
            listener()

    async def async_request_refresh(self) -> None:
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except Exception:
            self.last_update_success = False
        self.async_update_listeners()

    async def _async_update_data(self) -> Any:
        raise NotImplementedError


class CoordinatorEntity(Generic[_T]):
    """Mock CoordinatorEntity."""

    def __init__(self, coordinator: _T) -> None:
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)

    @property
    def available(self) -> bool:
        return getattr(self.coordinator, "last_update_success", True)


class UpdateFailed(Exception):
    """Mock UpdateFailed exception."""
    pass


class DeviceInfo(dict):
    """Mock DeviceInfo for testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


# Entity Base mocks
class Entity:
    """Mock Entity."""
    _attr_has_entity_name: bool = True
    _attr_unique_id: str | None = None
    _attr_name: str | None = None
    _attr_icon: str | None = None
    _attr_device_info: dict[str, Any] | None = None
    _attr_extra_state_attributes: dict[str, Any] | None = None

    def async_write_ha_state(self) -> None:
        pass


class ToggleEntity(Entity):
    pass


# Sensor mocks
class SensorEntity(Entity):
    _attr_native_value: Any = None
    _attr_native_unit_of_measurement: str | None = None
    _attr_state_class: Any = None
    _attr_device_class: Any = None


@dataclass(frozen=True)
class SensorEntityDescription:
    key: str
    name: str | None = None
    native_unit_of_measurement: str | None = None
    device_class: Any = None
    state_class: Any = None
    entity_category: Any = None
    icon: str | None = None
    entity_registry_enabled_default: bool = True


# Binary Sensor mocks
class BinarySensorEntity(Entity):
    _attr_is_on: bool | None = None


@dataclass(frozen=True)
class BinarySensorEntityDescription:
    key: str
    name: str | None = None
    device_class: Any = None
    entity_category: Any = None
    icon: str | None = None
    entity_registry_enabled_default: bool = True


# Number mocks
class NumberEntity(Entity):
    _attr_native_value: float | None = None
    _attr_native_min_value: float = 0
    _attr_native_max_value: float = 100
    _attr_native_step: float = 1
    _attr_mode: str = "auto"


@dataclass(frozen=True)
class NumberEntityDescription:
    key: str
    name: str | None = None
    native_unit_of_measurement: str | None = None
    device_class: Any = None
    native_min_value: float = 0
    native_max_value: float = 100
    native_step: float = 1
    mode: str = "auto"
    entity_category: Any = None
    icon: str | None = None


# Select mocks
class SelectEntity(Entity):
    _attr_current_option: str | None = None
    _attr_options: list[str] = []


@dataclass(frozen=True)
class SelectEntityDescription:
    key: str
    name: str | None = None
    options: list[str] | None = None
    entity_category: Any = None
    icon: str | None = None


# Switch mocks
class SwitchEntity(ToggleEntity):
    _attr_is_on: bool | None = None


@dataclass(frozen=True)
class SwitchEntityDescription:
    key: str
    name: str | None = None
    entity_category: Any = None
    icon: str | None = None


# Button mocks
class ButtonEntity(Entity):
    pass


@dataclass(frozen=True)
class ButtonEntityDescription:
    key: str
    name: str | None = None
    device_class: Any = None
    entity_category: Any = None
    icon: str | None = None


# Device class enums
class SensorDeviceClass(StrEnum):
    BATTERY = "battery"
    POWER = "power"
    TEMPERATURE = "temperature"
    VOLTAGE = "voltage"
    CURRENT = "current"
    SIGNAL_STRENGTH = "signal_strength"
    ENUM = "enum"
    TIMESTAMP = "timestamp"


class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


class BinarySensorDeviceClass(StrEnum):
    BATTERY_CHARGING = "battery_charging"
    CONNECTIVITY = "connectivity"
    HEAT = "heat"
    POWER = "power"
    PROBLEM = "problem"


class NumberDeviceClass(StrEnum):
    BATTERY = "battery"
    POWER = "power"


class NumberMode(StrEnum):
    AUTO = "auto"
    BOX = "box"
    SLIDER = "slider"


class EntityCategory(StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    NUMBER = "number"
    SELECT = "select"
    SWITCH = "switch"
    BUTTON = "button"


class UnitOfPower:
    WATT = "W"
    KILO_WATT = "kW"


class UnitOfTemperature:
    CELSIUS = "°C"


class UnitOfElectricPotential:
    VOLT = "V"


class UnitOfElectricCurrent:
    AMPERE = "A"


PERCENTAGE = "%"
SIGNAL_STRENGTH_DECIBELS_MILLIWATT = "dBm"

CONF_HOST = "host"
CONF_PORT = "port"


def async_get_clientsession(hass: Any) -> Any:
    return None
