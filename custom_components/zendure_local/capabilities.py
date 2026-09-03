"""Device capability matrix and write validation for Zendure Local Battery Control."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

from .const import (
    AC_MODE_CHARGE,
    AC_MODE_DISCHARGE,
    PROP_AC_MODE,
    PROP_GRID_REVERSE,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SMART_MODE,
    PROP_SOC_SET,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PropertyConstraint:
    """Defines constraints and acceptable boundaries for a writable property."""

    prop_name: str
    val_type: type
    min_val: int | float | None = None
    max_val: int | float | None = None
    allowed_values: list[Any] | None = None
    unit: str | None = None
    description: str = ""

    def validate(self, value: Any) -> tuple[bool, str | None]:
        """Validate an outgoing property value against constraints."""
        if not isinstance(value, self.val_type):
            # Check if coercible int
            if self.val_type is int and isinstance(value, (float, str)):
                try:
                    int_val = int(value)
                    if isinstance(value, float) and int_val != value:
                        return False, f"Property {self.prop_name} requires an integer, got float {value}"
                    value = int_val
                except (ValueError, TypeError):
                    return False, f"Property {self.prop_name} must be of type {self.val_type.__name__}, got {type(value).__name__}"
            elif self.val_type is bool and isinstance(value, (int, str)):
                value = bool(value)
            else:
                return False, f"Property {self.prop_name} must be of type {self.val_type.__name__}, got {type(value).__name__}"

        if self.allowed_values is not None and value not in self.allowed_values:
            return False, f"Property {self.prop_name} value {value} not in allowed options {self.allowed_values}"

        if self.min_val is not None and value < self.min_val:
            return False, f"Property {self.prop_name} value {value} below minimum allowable {self.min_val}"

        if self.max_val is not None and value > self.max_val:
            return False, f"Property {self.prop_name} value {value} exceeds maximum allowable {self.max_val}"

        return True, None


@dataclass
class DeviceCapability:
    """Defines the supported features, transports, and writable properties for a model."""

    model_key: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    read_only: bool = False
    max_charge_w: int = 2400
    max_discharge_w: int = 2400
    max_solar_w: int = 2400
    constraints: dict[str, PropertyConstraint] = field(default_factory=dict)

    def can_write(self, prop_name: str) -> bool:
        """Check if property is writable on this device."""
        if self.read_only:
            return False
        return prop_name in self.constraints

    def validate_payload(self, properties: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate entire dictionary of properties destined for /properties/write."""
        if self.read_only:
            return False, f"Device model {self.display_name} is operating in read-only mode"

        if not properties:
            return False, "Write properties dictionary cannot be empty"

        for prop_name, val in properties.items():
            if prop_name not in self.constraints:
                return False, f"Property '{prop_name}' is not supported or not writable on {self.display_name}"

            constraint = self.constraints[prop_name]
            is_valid, err = constraint.validate(val)
            if not is_valid:
                return False, err

        return True, None


def _build_standard_constraints(max_charge: int, max_discharge: int) -> dict[str, PropertyConstraint]:
    return {
        PROP_AC_MODE: PropertyConstraint(
            prop_name=PROP_AC_MODE,
            val_type=int,
            allowed_values=[AC_MODE_CHARGE, AC_MODE_DISCHARGE],
            description="1: Charge mode, 2: Discharge mode",
        ),
        PROP_INPUT_LIMIT: PropertyConstraint(
            prop_name=PROP_INPUT_LIMIT,
            val_type=int,
            min_val=0,
            max_val=max_charge,
            unit="W",
            description="AC Charge limit in Watts",
        ),
        PROP_OUTPUT_LIMIT: PropertyConstraint(
            prop_name=PROP_OUTPUT_LIMIT,
            val_type=int,
            min_val=0,
            max_val=max_discharge,
            unit="W",
            description="Home output discharge limit in Watts",
        ),
        PROP_SOC_SET: PropertyConstraint(
            prop_name=PROP_SOC_SET,
            val_type=int,
            min_val=70,
            max_val=100,
            unit="%",
            description="Target charge SOC limit percentage",
        ),
        PROP_MIN_SOC: PropertyConstraint(
            prop_name=PROP_MIN_SOC,
            val_type=int,
            min_val=0,
            max_val=50,
            unit="%",
            description="Minimum discharge SOC limit percentage",
        ),
        PROP_SMART_MODE: PropertyConstraint(
            prop_name=PROP_SMART_MODE,
            val_type=int,
            allowed_values=[0, 1],
            description="0: Persistent flash write, 1: Volatile memory write",
        ),
        PROP_GRID_REVERSE: PropertyConstraint(
            prop_name=PROP_GRID_REVERSE,
            val_type=int,
            allowed_values=[0, 1, 2],
            description="Reverse flow control",
        ),
    }


# Static Capability Matrix
CAPABILITY_MATRIX: dict[str, DeviceCapability] = {
    "solarflow_800": DeviceCapability(
        model_key="solarflow_800",
        display_name="SolarFlow 800",
        aliases=["solarflow800", "SolarFlow 800", "SolarFlow800"],
        max_charge_w=800,
        max_discharge_w=800,
        max_solar_w=800,
        constraints=_build_standard_constraints(800, 800),
    ),
    "solarflow_800_plus": DeviceCapability(
        model_key="solarflow_800_plus",
        display_name="SolarFlow 800 Plus",
        aliases=["solarflow800plus", "SolarFlow 800 Plus", "SolarFlow800 Plus", "SolarFlow800Plus"],
        max_charge_w=800,
        max_discharge_w=800,
        max_solar_w=800,
        constraints=_build_standard_constraints(800, 800),
    ),
    "solarflow_800_pro": DeviceCapability(
        model_key="solarflow_800_pro",
        display_name="SolarFlow 800 Pro",
        aliases=["solarflow800pro", "SolarFlow 800 Pro", "SolarFlow800 Pro", "SolarFlow800Pro"],
        max_charge_w=800,
        max_discharge_w=800,
        max_solar_w=1000,
        constraints=_build_standard_constraints(800, 800),
    ),
    "solarflow_1600_ac_plus": DeviceCapability(
        model_key="solarflow_1600_ac_plus",
        display_name="SolarFlow 1600 AC+",
        aliases=["solarflow1600ac+", "SolarFlow 1600 AC+", "SolarFlow1600 AC+", "SolarFlow1600AC+"],
        max_charge_w=1600,
        max_discharge_w=1200,
        max_solar_w=1600,
        constraints=_build_standard_constraints(1600, 1200),
    ),
    "solarflow_2400_ac": DeviceCapability(
        model_key="solarflow_2400_ac",
        display_name="SolarFlow 2400 AC",
        aliases=[
            "solarflow2400ac",
            "SolarFlow 2400 AC",
            "SolarFlow2400 AC",
            "SolarFlow2400AC",
            "hyper2000",
            "Hyper 2000",
            "Hyper2000",
        ],
        max_charge_w=2400,
        max_discharge_w=2400,
        max_solar_w=2400,
        constraints=_build_standard_constraints(2400, 2400),
    ),
    "solarflow_2400_ac_plus": DeviceCapability(
        model_key="solarflow_2400_ac_plus",
        display_name="SolarFlow 2400 AC+",
        aliases=["solarflow2400ac+", "SolarFlow 2400 AC+", "SolarFlow2400 AC+", "SolarFlow2400AC+"],
        max_charge_w=3200,
        max_discharge_w=2400,
        max_solar_w=2400,
        constraints=_build_standard_constraints(3200, 2400),
    ),
    "solarflow_2400_pro": DeviceCapability(
        model_key="solarflow_2400_pro",
        display_name="SolarFlow 2400 Pro",
        aliases=["solarflow2400pro", "SolarFlow 2400 Pro", "SolarFlow2400 Pro", "SolarFlow2400Pro"],
        max_charge_w=3200,
        max_discharge_w=2400,
        max_solar_w=3000,
        constraints=_build_standard_constraints(3200, 2400),
    ),
    "smartmeter_3ct": DeviceCapability(
        model_key="smartmeter_3ct",
        display_name="SmartMeter 3CT",
        aliases=["smartmeter3ct", "SmartMeter3CT", "SmartMeter 3CT"],
        read_only=True,
        max_charge_w=0,
        max_discharge_w=0,
        max_solar_w=0,
        constraints={},
    ),
}


def _normalize_name(name: str) -> str:
    """Normalize string by removing whitespace and special characters (preserving +) for matching."""
    return re.sub(r"[^a-zA-Z0-9+]", "", name).lower()


def get_device_capability(model_name: str | None) -> DeviceCapability:
    """Resolve a reported model string to a known capability profile.
    
    If the model is unrecognized, returns a safe generic read-only profile.
    """
    if not model_name:
        return DeviceCapability(
            model_key="unknown_generic",
            display_name="Generic Zendure Device (Read-Only)",
            read_only=True,
            constraints={},
        )

    norm_query = _normalize_name(model_name)

    # 1. Exact match on capability key or alias
    for cap in CAPABILITY_MATRIX.values():
        if norm_query == _normalize_name(cap.model_key):
            return cap
        for alias in cap.aliases:
            if norm_query == _normalize_name(alias):
                return cap

    # 2. Substring matching
    for cap in CAPABILITY_MATRIX.values():
        for alias in cap.aliases:
            norm_alias = _normalize_name(alias)
            if norm_alias and (norm_alias in norm_query or norm_query in norm_alias):
                return cap

    # 3. Fallback: Unknown device -> default to safe read-only
    _LOGGER.warning(
        "Device model '%s' not recognized in capability matrix. Operating in safe read-only mode.",
        model_name,
    )
    return DeviceCapability(
        model_key="unknown",
        display_name=f"Unknown ({model_name})",
        read_only=True,
        constraints={},
    )
