"""Tests for Zendure state model and property conversions."""

from custom_components.zendure_local.const import (
    STATE_CHARGING,
    STATE_DISCHARGING,
    STATE_STANDBY,
    STATE_UNKNOWN,
)
from custom_components.zendure_local.model import (
    convert_current_amps,
    convert_signed_int16,
    convert_temperature_kelvin_tenth,
    parse_pack_data,
    parse_report_payload,
)


def test_convert_temperature_kelvin_tenth():
    """Test temperature conversion from 0.1 Kelvin to Celsius."""
    # (2981 - 2731) / 10.0 = 25.0 C
    assert convert_temperature_kelvin_tenth(2981) == 25.0
    # (2731 - 2731) / 10.0 = 0.0 C
    assert convert_temperature_kelvin_tenth(2731) == 0.0
    # (2631 - 2731) / 10.0 = -10.0 C
    assert convert_temperature_kelvin_tenth(2631) == -10.0
    # None or invalid
    assert convert_temperature_kelvin_tenth(None) is None
    assert convert_temperature_kelvin_tenth("invalid") is None


def test_convert_signed_int16():
    """Test 16-bit two's complement conversion."""
    assert convert_signed_int16(0) == 0
    assert convert_signed_int16(100) == 100
    assert convert_signed_int16(32767) == 32767
    # Negative values
    assert convert_signed_int16(65535) == -1
    assert convert_signed_int16(65530) == -6
    assert convert_signed_int16(32768) == -32768
    assert convert_signed_int16(None) is None


def test_convert_current_amps():
    """Test conversion of 16-bit signed current to Amperes."""
    # Positive current: 50 -> 5.0 A
    assert convert_current_amps(50) == 5.0
    # Negative current: 65516 -> -20 -> -2.0 A
    assert convert_current_amps(65516) == -2.0
    assert convert_current_amps(None) is None


def test_parse_pack_data():
    """Test parsing of packData list."""
    raw = [
        {
            "sn": "BP001",
            "packType": 1,
            "socLevel": 92,
            "state": 1,
            "power": 450,
            "maxTemp": 2981,
            "totalVol": 51.2,
            "batcur": 90,
            "maxVol": 335,
            "minVol": 330,
            "softVersion": 204,
            "heatState": 1,
        }
    ]
    packs = parse_pack_data(raw)
    assert len(packs) == 1
    p = packs[0]
    assert p.sn == "BP001"
    assert p.soc_percent == 92
    assert p.state == STATE_CHARGING
    assert p.power_w == 450
    assert p.max_temp_c == 25.0
    assert p.total_vol_v == 51.2
    assert p.current_a == 9.0
    assert p.max_cell_vol_v == 3.35
    assert p.min_cell_vol_v == 3.30
    assert p.soft_version == 204
    assert p.heating is True


def test_parse_report_payload_basic():
    """Test parsing complete /properties/report payload."""
    payload = {
        "sn": "SF2400-TEST",
        "product": "SolarFlow2400 AC",
        "properties": {
            "electricLevel": 78,
            "packState": 2,
            "solarInputPower": 600,
            "solarPower1": 350,
            "solarPower2": 250,
            "gridInputPower": 10,
            "outputHomePower": 400,
            "outputPackPower": 0,
            "packInputPower": 400,
            "inputLimit": 1200,
            "outputLimit": 800,
            "acMode": 2,
            "socSet": 95,
            "minSoc": 10,
            "smartMode": 1,
            "rssi": -68,
            "faultLevel": 0,
            "is_error": 0,
            "gridState": 1,
            "reverseState": 0,
            "hyperTmp": 31.2,
        },
    }

    state = parse_report_payload(payload)
    assert state.serial == "SF2400-TEST"
    assert state.model == "SolarFlow2400 AC"
    assert state.soc_percent == 78
    assert state.battery_state == STATE_DISCHARGING
    assert state.solar_input_w == 600
    assert state.pv_channels_w == {1: 350, 2: 250}
    assert state.home_output_w == 400
    assert state.battery_discharge_w == 400
    assert state.battery_charge_w == 0
    assert state.ac_mode == 2
    assert state.input_limit_w == 1200
    assert state.output_limit_w == 800
    assert state.target_soc_percent == 95
    assert state.min_soc_percent == 10
    assert state.smart_mode == 1
    assert state.temperature_c == 31.2
    assert state.rssi_dbm == -68
    assert state.error is False
    assert state.grid_connected is True
    assert state.available is True
    assert state.stale is False


def test_parse_report_payload_preserves_existing_on_missing_fields():
    """Test that missing property fields do not erase last known state."""
    payload1 = {
        "sn": "SF2400-TEST",
        "product": "SolarFlow2400 AC",
        "properties": {
            "electricLevel": 80,
            "socSet": 90,
            "minSoc": 20,
            "inputLimit": 600,
        },
    }
    state1 = parse_report_payload(payload1)
    assert state1.soc_percent == 80
    assert state1.target_soc_percent == 90
    assert state1.min_soc_percent == 20

    # Payload 2 has empty properties (e.g. transient report missing keys)
    payload2 = {
        "sn": "SF2400-TEST",
        "product": "SolarFlow2400 AC",
        "properties": {},
    }
    state2 = parse_report_payload(payload2, existing_state=state1)
    assert state2.soc_percent == 80  # Preserved!
    assert state2.target_soc_percent == 90  # Preserved!
    assert state2.min_soc_percent == 20  # Preserved!
    assert state2.input_limit_w == 600  # Preserved!
