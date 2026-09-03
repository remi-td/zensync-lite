"""Tests for Zendure coordinator, write transactions, and confirmation."""

import asyncio
import pytest

from custom_components.zendure_local.const import (
    PROP_AC_MODE,
    PROP_OUTPUT_LIMIT,
    PROP_SMART_MODE,
    TRANSACTION_CONFIRMED,
    TRANSACTION_FAILED,
)
from custom_components.zendure_local.coordinator import ZendureCoordinator
from custom_components.zendure_local.transport.local_http import LocalHttpTransport


class DummyHass:
    """Mock HomeAssistant for coordinator tests."""

    def __init__(self) -> None:
        self.loop = asyncio.get_event_loop()

    def async_create_task(self, target):
        return self.loop.create_task(target)


@pytest.mark.asyncio
async def test_coordinator_poll_and_confirmation(mock_zendure_server):
    """Test coordinator state polling and write confirmation."""
    hass = DummyHass()
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
        volatile_writes=True,
    )
    try:
        # Initial poll
        state = await coordinator._async_update_data()
        assert state.serial == "SF2400A10001"
        assert state.soc_percent == 85
        assert state.available is True
        assert state.stale is False

        # Execute write: sets outputLimit and acMode
        success = await coordinator.async_execute_write(
            {PROP_OUTPUT_LIMIT: 400, PROP_AC_MODE: 2}
        )
        assert success is True
        assert coordinator.transaction_state == TRANSACTION_CONFIRMED

        # Verify device confirmed state
        current = coordinator.current_state
        assert current.output_limit_w == 400
        assert current.ac_mode == 2

        # Verify volatile write smartMode: 1 was injected
        assert mock_zendure_server.last_write["properties"][PROP_SMART_MODE] == 1
    finally:
        await coordinator.async_close()


@pytest.mark.asyncio
async def test_coordinator_confirmation_mismatch(mock_zendure_server):
    """Test that when a device reports a value different from requested, write fails."""
    hass = DummyHass()
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

        # Simulate device accepting HTTP POST but failing to actually apply the property
        mock_zendure_server.report_data["properties"]["outputLimit"] = 600
        mock_zendure_server.ignore_property_writes = True

        success = await coordinator.async_execute_write({PROP_OUTPUT_LIMIT: 500})
        # Confirmation should detect mismatch: expected 500, got 600
        assert success is False
        assert coordinator.transaction_state == TRANSACTION_FAILED
        assert "Confirmation mismatch" in coordinator.last_transaction_detail
    finally:
        await coordinator.async_close()


@pytest.mark.asyncio
async def test_coordinator_write_serialization(mock_zendure_server):
    """Test that concurrent writes are serialized with the write lock."""
    hass = DummyHass()
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

        # Add artificial delay to mock server writes
        mock_zendure_server.write_delay = 0.1

        # Run two writes concurrently
        results = await asyncio.gather(
            coordinator.async_execute_write({PROP_OUTPUT_LIMIT: 300}),
            coordinator.async_execute_write({PROP_OUTPUT_LIMIT: 400}),
        )

        assert all(results)
        # Verify both writes completed in sequence
        assert len(mock_zendure_server.write_history) == 2
        assert mock_zendure_server.write_history[0]["properties"]["outputLimit"] == 300
        assert mock_zendure_server.write_history[1]["properties"]["outputLimit"] == 400
    finally:
        await coordinator.async_close()


@pytest.mark.asyncio
async def test_coordinator_stale_threshold_and_state_preservation(mock_zendure_server):
    """Test that 3 failed polls marks data stale without clearing last known values."""
    hass = DummyHass()
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    rediscover_called = False

    def on_rediscover():
        nonlocal rediscover_called
        rediscover_called = True

    coordinator = ZendureCoordinator(
        hass=hass,
        transport=transport,
        serial="SF2400A10001",
        model="SolarFlow2400 AC",
        rediscover_callback=on_rediscover,
    )
    try:
        # Initial poll succeeds
        state = await coordinator._async_update_data()
        assert state.soc_percent == 85
        assert state.available is True
        assert state.stale is False

        # Turn on failures
        mock_zendure_server.should_fail_report = True

        # Failure 1: Still not stale, rediscovery callback triggered
        state1 = await coordinator._async_update_data()
        await asyncio.sleep(0.01)
        assert coordinator.consecutive_failed_polls == 1
        assert state1.stale is False
        assert state1.soc_percent == 85
        assert rediscover_called is True

        # Failure 2: Still not stale
        state2 = await coordinator._async_update_data()
        assert coordinator.consecutive_failed_polls == 2
        assert state2.stale is False

        # Failure 3: Reaches threshold of 3 -> marked stale & unavailable!
        state3 = await coordinator._async_update_data()
        assert coordinator.consecutive_failed_polls == 3
        assert state3.stale is True
        assert state3.available is False
        # IMPORTANT: Last known SOC and configuration are preserved!
        assert state3.soc_percent == 85
        assert state3.input_limit_w == 800
        assert state3.output_limit_w == 600
    finally:
        await coordinator.async_close()
