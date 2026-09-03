"""Tests for Zendure capability matrix and write validation."""

from custom_components.zendure_local.capabilities import (
    CAPABILITY_MATRIX,
    get_device_capability,
)
from custom_components.zendure_local.const import (
    PROP_AC_MODE,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SMART_MODE,
    PROP_SOC_SET,
)


def test_capability_alias_resolution():
    """Test resolution of various model names and aliases."""
    # Hyper 2000 resolves to solarflow_2400_ac
    cap_hyper = get_device_capability("Hyper 2000")
    assert cap_hyper.model_key == "solarflow_2400_ac"
    assert cap_hyper.max_charge_w == 2400
    assert cap_hyper.max_discharge_w == 2400

    # SolarFlow800
    cap_sf800 = get_device_capability("SolarFlow 800 Pro")
    assert cap_sf800.model_key == "solarflow_800_pro"
    assert cap_sf800.max_solar_w == 1000

    # SmartMeter3CT is read-only
    cap_meter = get_device_capability("SmartMeter3CT")
    assert cap_meter.read_only is True
    assert cap_meter.can_write(PROP_INPUT_LIMIT) is False

    # Unknown device defaults to read-only safe mode
    cap_unknown = get_device_capability("FutureZendureModel9999")
    assert cap_unknown.read_only is True
    assert cap_unknown.can_write(PROP_OUTPUT_LIMIT) is False


def test_validate_payload_success():
    """Test successful validation of valid properties."""
    cap = get_device_capability("SolarFlow 2400 AC")
    valid_payload = {
        PROP_AC_MODE: 2,
        PROP_OUTPUT_LIMIT: 500,
        PROP_INPUT_LIMIT: 0,
        PROP_SOC_SET: 90,
        PROP_MIN_SOC: 15,
        PROP_SMART_MODE: 1,
    }
    is_valid, err = cap.validate_payload(valid_payload)
    assert is_valid is True
    assert err is None


def test_validate_payload_out_of_range():
    """Test rejection of out-of-range values."""
    cap = get_device_capability("SolarFlow 800")

    # inputLimit exceeds 800W max for SolarFlow 800
    is_valid, err = cap.validate_payload({PROP_INPUT_LIMIT: 1200})
    assert is_valid is False
    assert "exceeds maximum allowable" in err

    # minSoc above 50%
    is_valid, err = cap.validate_payload({PROP_MIN_SOC: 60})
    assert is_valid is False
    assert "exceeds maximum allowable" in err

    # socSet below 70%
    is_valid, err = cap.validate_payload({PROP_SOC_SET: 65})
    assert is_valid is False
    assert "below minimum allowable" in err

    # acMode not in [1, 2]
    is_valid, err = cap.validate_payload({PROP_AC_MODE: 3})
    assert is_valid is False
    assert "not in allowed options" in err


def test_validate_payload_unsupported_property():
    """Test rejection of unsupported property."""
    cap = get_device_capability("SolarFlow 2400 AC")
    is_valid, err = cap.validate_payload({"non_existent_property": 100})
    assert is_valid is False
    assert "not supported" in err


def test_validate_payload_read_only_device():
    """Test rejection of any writes on read-only devices."""
    cap = get_device_capability("SmartMeter3CT")
    is_valid, err = cap.validate_payload({PROP_INPUT_LIMIT: 100})
    assert is_valid is False
    assert "read-only" in err
