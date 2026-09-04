"""Diagnostics support for Zendure Local Battery Control."""

from __future__ import annotations

from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
except ImportError:
    ConfigEntry = Any  # type: ignore
    HomeAssistant = Any  # type: ignore

from .const import CONF_HOST, CONF_PORT, CONF_SERIAL, DOMAIN, VERSION
from .coordinator import ZendureCoordinator


def redact_ip_address(ip: str | None) -> str:
    """Redact host or IP address for privacy in diagnostic dumps."""
    if not ip:
        return "unknown"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return f"{ip[:4]}***"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    host = entry.data.get(CONF_HOST)
    serial = coordinator.serial
    state = coordinator.current_state if coordinator else None

    # Redact serial for privacy, keep last 4 chars
    redacted_sn = f"***{serial[-4:]}" if len(serial) >= 4 else "***"

    diag_data: dict[str, Any] = {
        "integration": {
            "domain": DOMAIN,
            "version": VERSION,
        },
        "config_entry": {
            "entry_id": entry.entry_id,
            "host_redacted": redact_ip_address(host),
            "port": entry.data.get(CONF_PORT, 80),
            "serial_redacted": redacted_sn,
            "model": entry.data.get("model", "unknown"),
            "transport": entry.data.get("transport", "local_http"),
            "volatile_writes": entry.data.get("volatile_writes", True),
        },
        "device_state": None,
        "capabilities": None,
        "raw_property_keys": [],
    }

    if coordinator:
        diag_data["capabilities"] = {
            "model_key": coordinator.capability.model_key,
            "display_name": coordinator.capability.display_name,
            "read_only": coordinator.capability.read_only,
            "max_charge_w": coordinator.capability.max_charge_w,
            "max_discharge_w": coordinator.capability.max_discharge_w,
            "max_solar_w": coordinator.capability.max_solar_w,
            "writable_properties": list(coordinator.capability.constraints.keys()),
        }
        diag_data["transactions"] = {
            "state": coordinator.transaction_state,
            "last_time": coordinator.last_transaction_time.isoformat() if coordinator.last_transaction_time else None,
            "detail": coordinator.last_transaction_detail,
        }

    if state:
        diag_data["device_state"] = {
            "available": state.available,
            "stale": state.stale,
            "transport": state.transport,
            "last_seen": state.last_seen.isoformat() if state.last_seen else None,
            "soc_percent": state.soc_percent,
            "min_soc_percent": state.min_soc_percent,
            "target_soc_percent": state.target_soc_percent,
            "battery_state": state.battery_state,
            "solar_input_w": state.solar_input_w,
            "grid_input_w": state.grid_input_w,
            "home_output_w": state.home_output_w,
            "battery_charge_w": state.battery_charge_w,
            "battery_discharge_w": state.battery_discharge_w,
            "input_limit_w": state.input_limit_w,
            "output_limit_w": state.output_limit_w,
            "ac_mode": state.ac_mode,
            "smart_mode": state.smart_mode,
            "temperature_c": state.temperature_c,
            "rssi_dbm": state.rssi_dbm,
            "fault_level": state.fault_level,
            "error": state.error,
            "grid_connected": state.grid_connected,
            "reverse_flow_active": state.reverse_flow_active,
            "pack_count": len(state.pack_data),
        }
        diag_data["raw_property_keys"] = sorted(list(state.raw_properties.keys()))

    return diag_data
