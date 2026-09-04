"""Zendure Local Battery Control integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.const import CONF_HOST, CONF_PORT, Platform
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
except ImportError:
    from .compat import (  # type: ignore[no-redef]
        CONF_HOST,
        CONF_PORT,
        ConfigEntry,
        HomeAssistant,
        Platform,
        async_get_clientsession,
    )

from .const import (
    CONF_MODEL,
    CONF_SERIAL,
    CONF_VOLATILE_WRITES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import ZendureCoordinator
from .services import async_setup_services, async_unload_services
from .transport.local_http import LocalHttpTransport

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zendure Local from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    serial = entry.data[CONF_SERIAL]
    model = entry.data.get(CONF_MODEL, "SolarFlow")

    poll_interval = entry.options.get("poll_interval", DEFAULT_POLL_INTERVAL)
    volatile_writes = entry.options.get(
        CONF_VOLATILE_WRITES,
        entry.data.get(CONF_VOLATILE_WRITES, True),
    )

    session = async_get_clientsession(hass)
    transport = LocalHttpTransport(
        serial=serial,
        host=host,
        port=port,
        session=session,
    )

    coordinator = ZendureCoordinator(
        hass=hass,
        transport=transport,
        serial=serial,
        model=model,
        poll_interval_sec=poll_interval,
        volatile_writes=volatile_writes,
    )

    # Initial poll
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "transport": transport,
    }

    # Register platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register actions / services
    await async_setup_services(hass)

    # Watch for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data and "coordinator" in entry_data:
            await entry_data["coordinator"].async_close()

        await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
