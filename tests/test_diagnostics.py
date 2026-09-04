"""Tests for diagnostics and privacy redaction."""

import pytest

from custom_components.zensync_lite.coordinator import ZendureCoordinator
from custom_components.zensync_lite.diagnostics import (
    async_get_config_entry_diagnostics,
    redact_ip_address,
)
from custom_components.zensync_lite.transport.local_http import LocalHttpTransport


def test_redact_ip_address():
    """Test IP address redaction."""
    assert redact_ip_address("192.168.1.150") == "192.168.*.*"
    assert redact_ip_address("10.0.0.5") == "10.0.*.*"
    assert redact_ip_address("battery.local") == "batt***"
    assert redact_ip_address("") == "unknown"


@pytest.mark.asyncio
async def test_diagnostics_export(mock_zendure_server):
    """Test diagnostics export structure and redactions."""
    class MockEntry:
        entry_id = "test_entry_123"
        data = {
            "host": "192.168.1.88",
            "port": 80,
            "serial": "SF2400A10001",
            "model": "SolarFlow2400 AC",
            "transport": "local_http",
            "volatile_writes": True,
        }

    class MockHass:
        data = {}

    hass = MockHass()
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    coordinator = ZendureCoordinator(
        hass=None,
        transport=transport,
        serial="SF2400A10001",
        model="SolarFlow2400 AC",
    )
    try:
        await coordinator._async_update_data()
        hass.data["zensync_lite"] = {
            "test_entry_123": {
                "coordinator": coordinator,
            }
        }

        diag = await async_get_config_entry_diagnostics(hass, MockEntry())

        # Verify redactions
        assert diag["config_entry"]["host_redacted"] == "192.168.*.*"
        assert diag["config_entry"]["serial_redacted"] == "***0001"
        assert "192.168.1.88" not in str(diag)

        # Verify device state and capabilities
        assert diag["capabilities"]["model_key"] == "solarflow_2400_ac"
        assert diag["device_state"]["soc_percent"] == 85
        assert diag["device_state"]["battery_charge_w"] == 300
        assert "electricLevel" in diag["raw_property_keys"]
    finally:
        await coordinator.async_close()
