"""Services for Zendure Local Battery Control."""

from __future__ import annotations

import logging
from typing import Any

try:
    import voluptuous as vol
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers import config_validation as cv
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
except ImportError:
    vol = type("vol", (), {"Schema": lambda s: s, "Optional": lambda k, **kw: k, "Required": lambda k, **kw: k, "All": lambda *a: a, "Range": lambda **kw: kw, "In": lambda a: a})  # type: ignore
    cv = type("cv", (), {"string": str, "positive_int": int, "boolean": bool})  # type: ignore
    ServiceCall = Any  # type: ignore
    from .compat import HomeAssistant  # type: ignore[no-redef]

from .const import (
    AC_MODE_CHARGE,
    AC_MODE_DISCHARGE,
    ATTR_LIMIT,
    ATTR_MIN_SOC,
    ATTR_MODE,
    ATTR_TARGET_SOC,
    DOMAIN,
    MAP_STR_TO_AC_MODE,
    MODE_CHARGE_STR,
    MODE_DISCHARGE_STR,
    PROP_AC_MODE,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SOC_SET,
    SERVICE_REDISCOVER,
    SERVICE_REFRESH,
    SERVICE_SET_CHARGE_LIMIT,
    SERVICE_SET_MODE,
    SERVICE_SET_OUTPUT_LIMIT,
    SERVICE_SET_SOC_LIMITS,
    SERVICE_STOP_OUTPUT,
)
from .coordinator import ZendureCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_coordinators_for_call(hass: HomeAssistant, call: ServiceCall) -> list[ZendureCoordinator]:
    """Resolve target device_id or entity_id to a list of matching Zendure coordinators."""
    coordinators: list[ZendureCoordinator] = []
    domain_data = hass.data.get(DOMAIN, {})

    target_device_ids = call.data.get("device_id", [])
    if isinstance(target_device_ids, str):
        target_device_ids = [target_device_ids]

    target_entity_ids = call.data.get("entity_id", [])
    if isinstance(target_entity_ids, str):
        target_entity_ids = [target_entity_ids]

    if not target_device_ids and not target_entity_ids:
        # Target all configured coordinators if none specified
        for entry_info in domain_data.values():
            if isinstance(entry_info, dict) and "coordinator" in entry_info:
                coordinators.append(entry_info["coordinator"])
        return coordinators

    # Match by device_id
    if target_device_ids:
        try:
            device_reg = dr.async_get(hass)
            for dev_id in target_device_ids:
                device = device_reg.async_get(dev_id)
                if not device:
                    continue
                for identifier in device.identifiers:
                    if identifier[0] == DOMAIN:
                        serial = identifier[1]
                        for entry_info in domain_data.values():
                            coord = entry_info.get("coordinator")
                            if coord and coord.serial == serial and coord not in coordinators:
                                coordinators.append(coord)
        except Exception:
            pass

    # Match by entity_id
    if target_entity_ids:
        try:
            entity_reg = er.async_get(hass)
            for ent_id in target_entity_ids:
                entry = entity_reg.async_get(ent_id)
                if not entry:
                    continue
                # Entity unique ID format is zendure_local_<serial>_<key>
                if entry.unique_id and entry.unique_id.startswith(f"{DOMAIN}_"):
                    parts = entry.unique_id.split("_")
                    if len(parts) >= 3:
                        serial = parts[2]
                        for entry_info in domain_data.values():
                            coord = entry_info.get("coordinator")
                            if coord and coord.serial == serial and coord not in coordinators:
                                coordinators.append(coord)
        except Exception:
            pass

    return coordinators


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register all zendure_local action services."""

    async def handle_set_charge_limit(call: ServiceCall) -> None:
        limit = call.data[ATTR_LIMIT]
        for coord in _get_coordinators_for_call(hass, call):
            _LOGGER.info("Service set_charge_limit for %s: %dW", coord.serial, limit)
            await coord.async_execute_write({PROP_INPUT_LIMIT: limit})

    async def handle_set_output_limit(call: ServiceCall) -> None:
        limit = call.data[ATTR_LIMIT]
        for coord in _get_coordinators_for_call(hass, call):
            _LOGGER.info("Service set_output_limit for %s: %dW", coord.serial, limit)
            await coord.async_execute_write({PROP_OUTPUT_LIMIT: limit})

    async def handle_set_mode(call: ServiceCall) -> None:
        mode_val = call.data[ATTR_MODE]
        if isinstance(mode_val, str):
            raw_mode = MAP_STR_TO_AC_MODE.get(mode_val.lower())
        else:
            raw_mode = int(mode_val)

        if raw_mode not in (AC_MODE_CHARGE, AC_MODE_DISCHARGE):
            _LOGGER.error("Invalid mode value provided: %s", mode_val)
            return

        for coord in _get_coordinators_for_call(hass, call):
            _LOGGER.info("Service set_mode for %s: %s (%d)", coord.serial, mode_val, raw_mode)
            await coord.async_execute_write({PROP_AC_MODE: raw_mode})

    async def handle_set_soc_limits(call: ServiceCall) -> None:
        min_soc = call.data.get(ATTR_MIN_SOC)
        target_soc = call.data.get(ATTR_TARGET_SOC)
        props: dict[str, Any] = {}
        if min_soc is not None:
            props[PROP_MIN_SOC] = int(min_soc)
        if target_soc is not None:
            props[PROP_SOC_SET] = int(target_soc)

        if not props:
            return

        for coord in _get_coordinators_for_call(hass, call):
            _LOGGER.info("Service set_soc_limits for %s: %s", coord.serial, props)
            await coord.async_execute_write(props)

    async def handle_stop_output(call: ServiceCall) -> None:
        for coord in _get_coordinators_for_call(hass, call):
            _LOGGER.info("Service stop_output for %s", coord.serial)
            # Setting outputLimit to 0 stops home discharge safely
            await coord.async_execute_write({PROP_OUTPUT_LIMIT: 0})

    async def handle_refresh(call: ServiceCall) -> None:
        for coord in _get_coordinators_for_call(hass, call):
            await coord.async_request_refresh()

    async def handle_rediscover(call: ServiceCall) -> None:
        for coord in _get_coordinators_for_call(hass, call):
            await coord._async_try_rediscover()

    services_to_register = [
        (SERVICE_SET_CHARGE_LIMIT, handle_set_charge_limit),
        (SERVICE_SET_OUTPUT_LIMIT, handle_set_output_limit),
        (SERVICE_SET_MODE, handle_set_mode),
        (SERVICE_SET_SOC_LIMITS, handle_set_soc_limits),
        (SERVICE_STOP_OUTPUT, handle_stop_output),
        (SERVICE_REFRESH, handle_refresh),
        (SERVICE_REDISCOVER, handle_rediscover),
    ]

    for svc_name, handler in services_to_register:
        if not hass.services.has_service(DOMAIN, svc_name):
            hass.services.async_register(DOMAIN, svc_name, handler)


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister all services when integration is completely unloaded."""
    domain_data = hass.data.get(DOMAIN, {})
    # Only remove services if no other config entries remain
    if len(domain_data) <= 1:
        services_to_remove = [
            SERVICE_SET_CHARGE_LIMIT,
            SERVICE_SET_OUTPUT_LIMIT,
            SERVICE_SET_MODE,
            SERVICE_SET_SOC_LIMITS,
            SERVICE_STOP_OUTPUT,
            SERVICE_REFRESH,
            SERVICE_REDISCOVER,
        ]
        for svc in services_to_remove:
            if hass.services.has_service(DOMAIN, svc):
                hass.services.async_remove(DOMAIN, svc)
