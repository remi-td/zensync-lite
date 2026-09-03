"""Tests for explicit action services."""

import asyncio
import pytest

from custom_components.zendure_local.const import (
    DOMAIN,
    PROP_AC_MODE,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SOC_SET,
    SERVICE_SET_CHARGE_LIMIT,
    SERVICE_SET_MODE,
    SERVICE_SET_OUTPUT_LIMIT,
    SERVICE_SET_SOC_LIMITS,
    SERVICE_STOP_OUTPUT,
)
from custom_components.zendure_local.coordinator import ZendureCoordinator
from custom_components.zendure_local.services import async_setup_services
from custom_components.zendure_local.transport.local_http import LocalHttpTransport


class MockServices:
    def __init__(self):
        self.handlers = {}

    def has_service(self, domain, service):
        return (domain, service) in self.handlers

    def async_register(self, domain, service, handler):
        self.handlers[(domain, service)] = handler

    async def async_call(self, domain, service, data):
        handler = self.handlers[(domain, service)]
        call = type("Call", (), {"data": data})()
        await handler(call)


class MockHassWithServices:
    def __init__(self):
        self.services = MockServices()
        self.data = {}
        self.loop = asyncio.get_event_loop()


@pytest.mark.asyncio
async def test_services_execution(mock_zendure_server):
    """Test calling zendure_local action services."""
    hass = MockHassWithServices()
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    coordinator = ZendureCoordinator(
        hass=hass,
        transport=transport,
        serial="SF2400A10001",
        model="SolarFlow2400 AC",
    )
    try:
        await coordinator._async_update_data()
        hass.data[DOMAIN] = {
            "entry_1": {
                "coordinator": coordinator,
            }
        }

        await async_setup_services(hass)

        # 1. set_charge_limit
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_CHARGE_LIMIT,
            {"limit": 750},
        )
        assert mock_zendure_server.last_write["properties"][PROP_INPUT_LIMIT] == 750

        # 2. set_output_limit
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_OUTPUT_LIMIT,
            {"limit": 450},
        )
        assert mock_zendure_server.last_write["properties"][PROP_OUTPUT_LIMIT] == 450

        # 3. set_mode
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_MODE,
            {"mode": "discharge"},
        )
        assert mock_zendure_server.last_write["properties"][PROP_AC_MODE] == 2

        # 4. set_soc_limits
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SOC_LIMITS,
            {"min_soc": 20, "target_soc": 85},
        )
        assert mock_zendure_server.last_write["properties"][PROP_MIN_SOC] == 20
        assert mock_zendure_server.last_write["properties"][PROP_SOC_SET] == 85

        # 5. stop_output
        await hass.services.async_call(
            DOMAIN,
            SERVICE_STOP_OUTPUT,
            {},
        )
        assert mock_zendure_server.last_write["properties"][PROP_OUTPUT_LIMIT] == 0
    finally:
        await coordinator.async_close()
