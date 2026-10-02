"""Tests for Zendure Local config flow."""

import pytest

from custom_components.zensync_lite.config_flow import (
    ZeroconfServiceInfo,
    ZendureConfigFlow,
    _extract_model_from_name,
    _extract_serial_from_name,
)
from custom_components.zensync_lite.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SERIAL,
    CONF_TRANSPORT,
    CONF_VOLATILE_WRITES,
    TRANSPORT_LOCAL_HTTP,
)


def test_name_extractors():
    """Test extracting model and serial from mDNS service names."""
    name1 = "Zendure-SolarFlow800-WOB1NHMAMXXXXX3._zendure._tcp.local."
    assert _extract_model_from_name(name1) == "SolarFlow800"
    assert _extract_serial_from_name(name1) == "WOB1NHMAMXXXXX3"

    name2 = "Zendure-SolarFlow2400AC-001122334455._zendure._tcp."
    assert _extract_model_from_name(name2) == "SolarFlow2400AC"
    assert _extract_serial_from_name(name2) == "001122334455"


@pytest.mark.asyncio
async def test_config_flow_manual_setup(mock_zendure_server):
    """Test manual configuration flow."""
    flow = ZendureConfigFlow()

    # Step user with input
    result = await flow.async_step_user(
        {
            CONF_HOST: "127.0.0.1",
            CONF_PORT: mock_zendure_server.port,
            CONF_VOLATILE_WRITES: True,
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "127.0.0.1"
    assert result["data"][CONF_PORT] == mock_zendure_server.port
    assert result["data"][CONF_SERIAL] == "SF2400A10001"
    assert result["data"][CONF_MODEL] == "SolarFlow2400 AC"
    assert result["data"][CONF_TRANSPORT] == TRANSPORT_LOCAL_HTTP
    assert result["data"][CONF_VOLATILE_WRITES] is True


@pytest.mark.asyncio
async def test_config_flow_zeroconf_discovery(mock_zendure_server):
    """Test mDNS discovery flow."""
    flow = ZendureConfigFlow()

    info = ZeroconfServiceInfo()
    info.host = "127.0.0.1"
    info.port = mock_zendure_server.port
    info.name = "Zendure-SolarFlow2400AC-SF2400A10001._zendure._tcp.local."

    result = await flow.async_step_zeroconf(info)
    assert result["type"] == "form"
    assert result["step_id"] == "zeroconf_confirm"

    # Confirm discovery
    confirm_res = await flow.async_step_zeroconf_confirm(user_input={})
    assert confirm_res["type"] == "create_entry"
    assert confirm_res["data"][CONF_SERIAL] == "SF2400A10001"


@pytest.mark.asyncio
async def test_config_flow_cannot_connect():
    """Test error handling when host cannot be connected."""
    flow = ZendureConfigFlow()
    result = await flow.async_step_user(
        {
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 59998,
        }
    )
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_options_flow(mock_zendure_server):
    """Test options flow initialization and submission without 500 error."""
    from custom_components.zensync_lite.compat import ConfigEntry

    entry = ConfigEntry(
        entry_id="test_entry_id",
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: mock_zendure_server.port,
            CONF_SERIAL: "SF2400A10001",
        },
        options={
            CONF_VOLATILE_WRITES: True,
            "poll_interval": 10,
        },
    )

    flow = ZendureConfigFlow.async_get_options_flow(entry)
    form_res = await flow.async_step_init()
    assert form_res["type"] == "form"
    assert form_res["step_id"] == "init"

    save_res = await flow.async_step_init(
        user_input={
            CONF_HOST: "192.168.1.136",
            CONF_PORT: 80,
            CONF_VOLATILE_WRITES: True,
            "poll_interval": 15,
        }
    )
    assert save_res["type"] == "create_entry"
    assert save_res["data"][CONF_HOST] == "192.168.1.136"
    assert save_res["data"]["poll_interval"] == 15

