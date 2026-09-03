"""Tests for multi-device unique ID collision prevention."""

from custom_components.zendure_local.button import BUTTON_DESCRIPTIONS, ZendureButton
from custom_components.zendure_local.coordinator import ZendureCoordinator
from custom_components.zendure_local.number import NUMBER_DESCRIPTIONS, ZendureNumber
from custom_components.zendure_local.select import ZendureModeSelect
from custom_components.zendure_local.sensor import CORE_SENSORS, ZendureSensor
from custom_components.zendure_local.switch import ZendureSmartModeSwitch
from custom_components.zendure_local.transport.local_http import LocalHttpTransport


def test_multi_device_unique_ids():
    """Verify that identical device models have 100% unique IDs across all entity types."""
    serial_a = "SF2400_UNIT_A"
    serial_b = "SF2400_UNIT_B"

    coord_a = ZendureCoordinator(
        hass=None,
        transport=LocalHttpTransport(serial=serial_a, host="192.168.1.10", port=80),
        serial=serial_a,
        model="SolarFlow2400 AC",
    )
    coord_b = ZendureCoordinator(
        hass=None,
        transport=LocalHttpTransport(serial=serial_b, host="192.168.1.11", port=80),
        serial=serial_b,
        model="SolarFlow2400 AC",
    )

    all_ids: set[str] = set()
    total_entities = 0

    # Sensors
    for desc in CORE_SENSORS:
        ent_a = ZendureSensor(coord_a, desc)
        ent_b = ZendureSensor(coord_b, desc)
        assert ent_a.unique_id != ent_b.unique_id
        assert serial_a in ent_a.unique_id
        assert serial_b in ent_b.unique_id
        assert ent_a.unique_id.startswith(f"zendure_local_{serial_a}_")
        assert ent_b.unique_id.startswith(f"zendure_local_{serial_b}_")
        all_ids.add(ent_a.unique_id)
        all_ids.add(ent_b.unique_id)
        total_entities += 2

    # Numbers
    for desc in NUMBER_DESCRIPTIONS:
        num_a = ZendureNumber(coord_a, desc)
        num_b = ZendureNumber(coord_b, desc)
        assert num_a.unique_id != num_b.unique_id
        all_ids.add(num_a.unique_id)
        all_ids.add(num_b.unique_id)
        total_entities += 2

    # Select
    sel_a = ZendureModeSelect(coord_a)
    sel_b = ZendureModeSelect(coord_b)
    assert sel_a.unique_id != sel_b.unique_id
    all_ids.add(sel_a.unique_id)
    all_ids.add(sel_b.unique_id)
    total_entities += 2

    # Switch
    sw_a = ZendureSmartModeSwitch(coord_a)
    sw_b = ZendureSmartModeSwitch(coord_b)
    assert sw_a.unique_id != sw_b.unique_id
    all_ids.add(sw_a.unique_id)
    all_ids.add(sw_b.unique_id)
    total_entities += 2

    # Buttons
    for desc in BUTTON_DESCRIPTIONS:
        btn_a = ZendureButton(coord_a, desc)
        btn_b = ZendureButton(coord_b, desc)
        assert btn_a.unique_id != btn_b.unique_id
        all_ids.add(btn_a.unique_id)
        all_ids.add(btn_b.unique_id)
        total_entities += 2

    # Zero collisions: the number of unique IDs must equal total entities created
    assert len(all_ids) == total_entities
