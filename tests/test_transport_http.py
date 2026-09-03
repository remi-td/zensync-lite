"""Tests for LocalHttpTransport against mock aiohttp server."""

import pytest

from custom_components.zendure_local.transport.base import (
    TransportConnectionError,
    TransportError,
    TransportTimeoutError,
)
from custom_components.zendure_local.transport.local_http import LocalHttpTransport


@pytest.mark.asyncio
async def test_fetch_state_success(mock_zendure_server):
    """Test successful GET /properties/report."""
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    try:
        report = await transport.async_fetch_state()
        assert report["sn"] == "SF2400A10001"
        assert report["product"] == "SolarFlow2400 AC"
        assert report["properties"]["electricLevel"] == 85
        assert transport.consecutive_failures == 0
    finally:
        await transport.async_close()


@pytest.mark.asyncio
async def test_fetch_state_server_error(mock_zendure_server):
    """Test error handling when server returns 500."""
    mock_zendure_server.should_fail_report = True
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    try:
        with pytest.raises(TransportError):
            await transport.async_fetch_state()
        assert transport.consecutive_failures == 1
    finally:
        await transport.async_close()


@pytest.mark.asyncio
async def test_fetch_state_connection_error():
    """Test connection error to offline host."""
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=59999,  # Non-listening port
    )
    try:
        with pytest.raises(TransportConnectionError):
            await transport.async_fetch_state()
        assert transport.consecutive_failures == 1
    finally:
        await transport.async_close()


@pytest.mark.asyncio
async def test_write_properties_success(mock_zendure_server):
    """Test successful POST /properties/write with minimal payload."""
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
    )
    try:
        result = await transport.async_write_properties({"outputLimit": 350, "acMode": 2})
        assert result is True
        assert mock_zendure_server.last_write == {
            "sn": "SF2400A10001",
            "properties": {"outputLimit": 350, "acMode": 2},
        }
        # Verify device report updated
        report = await transport.async_fetch_state()
        assert report["properties"]["outputLimit"] == 350
        assert report["properties"]["acMode"] == 2
    finally:
        await transport.async_close()


@pytest.mark.asyncio
async def test_write_properties_retry_and_failure(mock_zendure_server):
    """Test that failed writes are retried and eventually raise error."""
    mock_zendure_server.should_fail_write = True
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="127.0.0.1",
        port=mock_zendure_server.port,
        max_retries=1,
    )
    try:
        with pytest.raises(TransportError):
            await transport.async_write_properties({"outputLimit": 300})
        # Verify 2 attempts were made (initial + 1 retry)
        assert len(mock_zendure_server.write_history) == 2
    finally:
        await transport.async_close()


@pytest.mark.asyncio
async def test_update_endpoint(mock_zendure_server):
    """Test updating transport host/port after IP change."""
    transport = LocalHttpTransport(
        serial="SF2400A10001",
        host="192.168.1.50",
        port=80,
    )
    assert transport.host == "192.168.1.50"
    transport.update_endpoint("127.0.0.1", mock_zendure_server.port)
    assert transport.host == "127.0.0.1"
    assert transport.port == mock_zendure_server.port

    try:
        report = await transport.async_fetch_state()
        assert report["sn"] == "SF2400A10001"
    finally:
        await transport.async_close()
