"""State and data models for Zendure Local Battery Control."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from .const import (
    MAP_PACK_STATE,
    PROP_AC_MODE,
    PROP_ELECTRIC_LEVEL,
    PROP_FAULT_LEVEL,
    PROP_GRID_INPUT_POWER,
    PROP_GRID_REVERSE,
    PROP_GRID_STATE,
    PROP_HEAT_STATE,
    PROP_HYPER_TMP,
    PROP_INPUT_LIMIT,
    PROP_IS_ERROR,
    PROP_MIN_SOC,
    PROP_OUTPUT_HOME_POWER,
    PROP_OUTPUT_LIMIT,
    PROP_OUTPUT_PACK_POWER,
    PROP_PACK_INPUT_POWER,
    PROP_PACK_STATE,
    PROP_PASS,
    PROP_REMAIN_OUT_TIME,
    PROP_REVERSE_STATE,
    PROP_RSSI,
    PROP_SMART_MODE,
    PROP_SOC_SET,
    PROP_SOLAR_INPUT_POWER,
    STATE_UNKNOWN,
    TRANSACTION_IDLE,
    TRANSPORT_LOCAL_HTTP,
)

_LOGGER = logging.getLogger(__name__)


def convert_temperature_kelvin_tenth(raw: int | None) -> float | None:
    """Convert raw temperature stored in 0.1 Kelvin to Celsius.
    
    Formula from ZenSDK docs: maxTemp_C = (maxTemp - 2731) / 10.0
    """
    if raw is None:
        return None
    try:
        val = float(raw)
        return round((val - 2731.0) / 10.0, 1)
    except (ValueError, TypeError):
        return None


def convert_signed_int16(val: int | None) -> int | None:
    """Convert an unsigned 16-bit value to a signed 16-bit integer (two's complement)."""
    if val is None:
        return None
    try:
        v = int(val) & 0xFFFF
        if v >= 0x8000:
            v -= 0x10000
        return v
    except (ValueError, TypeError):
        return None


def convert_current_amps(raw: int | None) -> float | None:
    """Convert raw battery current (16-bit two's complement) to Amperes.
    
    Formula from ZenSDK docs: current_A = value / 10.0
    """
    signed_val = convert_signed_int16(raw)
    if signed_val is None:
        return None
    return round(signed_val / 10.0, 2)


@dataclass
class ZendurePackState:
    """State of an individual battery pack connected to the system."""

    sn: str
    pack_type: int | None = None
    soc_percent: int | None = None
    state: str = STATE_UNKNOWN
    power_w: int | None = None
    max_temp_c: float | None = None
    total_vol_v: float | None = None
    current_a: float | None = None
    max_cell_vol_v: float | None = None
    min_cell_vol_v: float | None = None
    soft_version: int | None = None
    heating: bool | None = None


@dataclass
class ZendureBatteryState:
    """Normalized device telemetry and configuration state."""

    serial: str
    model: str
    firmware: dict[str, Any] = field(default_factory=dict)
    available: bool = False
    transport: str = TRANSPORT_LOCAL_HTTP
    last_seen: datetime | None = None
    stale: bool = False

    # Core Battery Telemetry
    soc_percent: int | None = None
    min_soc_percent: int | None = None
    target_soc_percent: int | None = None
    battery_state: str = STATE_UNKNOWN

    # Power Flows (Watts)
    solar_input_w: int | None = None
    pv_channels_w: dict[int, int] = field(default_factory=dict)
    grid_input_w: int | None = None
    home_output_w: int | None = None
    battery_charge_w: int | None = None     # outputPackPower: power flowing into battery
    battery_discharge_w: int | None = None  # packInputPower: power flowing out of battery

    # Limits and Controls
    input_limit_w: int | None = None
    output_limit_w: int | None = None
    ac_mode: int | None = None
    smart_mode: int | None = None
    grid_reverse: int | None = None

    # Environment & Diagnostics
    temperature_c: float | None = None
    rssi_dbm: int | None = None
    fault_level: int | None = None
    error: bool | None = None
    grid_connected: bool | None = None
    reverse_flow_active: bool | None = None
    pass_through: bool | None = None
    heating: bool | None = None
    remain_out_time_min: int | None = None

    # Transaction Tracking
    last_transaction_state: str = TRANSACTION_IDLE
    last_transaction_detail: str | None = None

    # Battery Packs
    pack_data: list[ZendurePackState] = field(default_factory=list)

    # Raw property dictionary for diagnostics
    raw_properties: dict[str, Any] = field(default_factory=dict)


def parse_pack_data(raw_packs: list[dict[str, Any]]) -> list[ZendurePackState]:
    """Parse list of battery pack dictionaries from ZenSDK report."""
    parsed: list[ZendurePackState] = []
    for item in raw_packs:
        if not isinstance(item, dict):
            continue
        sn = str(item.get("sn", "")).strip()
        if not sn:
            continue

        state_code = item.get("state")
        pack_state = MAP_PACK_STATE.get(state_code, STATE_UNKNOWN) if state_code is not None else STATE_UNKNOWN

        max_vol = item.get("maxVol")
        max_vol_v = round(max_vol / 100.0, 2) if max_vol is not None else None

        min_vol = item.get("minVol")
        min_vol_v = round(min_vol / 100.0, 2) if min_vol is not None else None

        total_vol = item.get("totalVol")
        total_vol_v = None
        if total_vol is not None:
            v_flt = float(total_vol)
            total_vol_v = round(v_flt / 100.0, 2) if v_flt > 500 else round(v_flt, 2)

        pack = ZendurePackState(
            sn=sn,
            pack_type=item.get("packType"),
            soc_percent=item.get("socLevel"),
            state=pack_state,
            power_w=item.get("power"),
            max_temp_c=convert_temperature_kelvin_tenth(item.get("maxTemp")),
            total_vol_v=total_vol_v,
            current_a=convert_current_amps(item.get("batcur")),
            max_cell_vol_v=max_vol_v,
            min_cell_vol_v=min_vol_v,
            soft_version=item.get("softVersion"),
            heating=bool(item.get("heatState")) if item.get("heatState") is not None else None,
        )
        parsed.append(pack)
    return parsed


def parse_report_payload(
    payload: dict[str, Any],
    serial_hint: str = "",
    model_hint: str = "",
    existing_state: ZendureBatteryState | None = None,
    transport: str = TRANSPORT_LOCAL_HTTP,
) -> ZendureBatteryState:
    """Parse a GET /properties/report payload into a normalized ZendureBatteryState."""
    sn = str(payload.get("sn") or serial_hint).strip()
    product = str(payload.get("product") or model_hint).strip()

    raw_props = payload.get("properties") or {}
    if not isinstance(raw_props, dict):
        raw_props = {}

    # PV Channels (solarPower1 .. solarPower6)
    pv_channels: dict[int, int] = {}
    for i in range(1, 7):
        k = f"solarPower{i}"
        if k in raw_props and raw_props[k] is not None:
            try:
                pv_channels[i] = int(raw_props[k])
            except (ValueError, TypeError):
                pass

    # Determine overall battery operational state
    raw_pack_state = raw_props.get(PROP_PACK_STATE)
    battery_state = MAP_PACK_STATE.get(raw_pack_state, STATE_UNKNOWN) if raw_pack_state is not None else STATE_UNKNOWN

    # If packState is unknown, check outputPackPower vs packInputPower
    if battery_state == STATE_UNKNOWN:
        charge_w = raw_props.get(PROP_OUTPUT_PACK_POWER, 0) or 0
        discharge_w = raw_props.get(PROP_PACK_INPUT_POWER, 0) or 0
        if charge_w > 10:
            battery_state = MAP_PACK_STATE.get(1, STATE_UNKNOWN)
        elif discharge_w > 10:
            battery_state = MAP_PACK_STATE.get(2, STATE_UNKNOWN)
        elif charge_w == 0 and discharge_w == 0:
            battery_state = MAP_PACK_STATE.get(0, STATE_UNKNOWN)

    # Temperature from hyperTmp (or highest pack temp if hyperTmp is not set)
    temp_c = None
    if PROP_HYPER_TMP in raw_props and raw_props[PROP_HYPER_TMP] is not None:
        try:
            raw_tmp = float(raw_props[PROP_HYPER_TMP])
            if raw_tmp > 1000:
                temp_c = convert_temperature_kelvin_tenth(int(raw_tmp))
            else:
                temp_c = raw_tmp
        except (ValueError, TypeError):
            temp_c = None

    raw_pack_data = payload.get("packData") or []
    packs = parse_pack_data(raw_pack_data) if isinstance(raw_pack_data, list) else []

    if temp_c is None and packs:
        pack_temps = [p.max_temp_c for p in packs if p.max_temp_c is not None]
        if pack_temps:
            temp_c = max(pack_temps)

    def _normalize_soc_pct(val: Any, is_min_soc: bool = False) -> int | None:
        if val is None:
            return None
        try:
            v = int(val)
            if v > 100:
                return round(v / 10)
            if is_min_soc and v == 100:
                # Minimum SOC cannot be 100% (range is 0-50%), so 100 represents 10.0%
                return 10
            return v
        except (ValueError, TypeError):
            return None

    soc = raw_props.get(PROP_ELECTRIC_LEVEL)
    if soc is None and existing_state:
        soc = existing_state.soc_percent

    min_soc = _normalize_soc_pct(raw_props.get(PROP_MIN_SOC), is_min_soc=True)
    if min_soc is None and existing_state:
        min_soc = existing_state.min_soc_percent

    soc_set = _normalize_soc_pct(raw_props.get(PROP_SOC_SET))
    if soc_set is None and existing_state:
        soc_set = existing_state.target_soc_percent
    if soc_set is None and existing_state:
        soc_set = existing_state.target_soc_percent

    in_limit = raw_props.get(PROP_INPUT_LIMIT)
    if in_limit is None and existing_state:
        in_limit = existing_state.input_limit_w

    out_limit = raw_props.get(PROP_OUTPUT_LIMIT)
    if out_limit is None and existing_state:
        out_limit = existing_state.output_limit_w

    ac_mode = raw_props.get(PROP_AC_MODE)
    if ac_mode is None and existing_state:
        ac_mode = existing_state.ac_mode

    smart_mode = raw_props.get(PROP_SMART_MODE)
    if smart_mode is None and existing_state:
        smart_mode = existing_state.smart_mode

    is_err = raw_props.get(PROP_IS_ERROR)
    has_error = bool(is_err) if is_err is not None else (existing_state.error if existing_state else False)

    grid_st = raw_props.get(PROP_GRID_STATE)
    grid_conn = bool(grid_st) if grid_st is not None else (existing_state.grid_connected if existing_state else None)

    rev_st = raw_props.get(PROP_REVERSE_STATE)
    rev_active = bool(rev_st) if rev_st is not None else (existing_state.reverse_flow_active if existing_state else None)

    pass_st = raw_props.get(PROP_PASS)
    pass_through = bool(pass_st) if pass_st is not None else (existing_state.pass_through if existing_state else None)

    heat_st = raw_props.get(PROP_HEAT_STATE)
    heating = bool(heat_st) if heat_st is not None else (existing_state.heating if existing_state else None)

    firmware_info: dict[str, Any] = {
        "version": payload.get("version"),
    }
    if packs and packs[0].soft_version is not None:
        firmware_info["pack_software_version"] = packs[0].soft_version

    return ZendureBatteryState(
        serial=sn,
        model=product,
        firmware=firmware_info,
        available=True,
        transport=transport,
        last_seen=datetime.now(timezone.utc),
        stale=False,
        soc_percent=soc,
        min_soc_percent=min_soc,
        target_soc_percent=soc_set,
        battery_state=battery_state,
        solar_input_w=raw_props.get(PROP_SOLAR_INPUT_POWER),
        pv_channels_w=pv_channels,
        grid_input_w=raw_props.get(PROP_GRID_INPUT_POWER),
        home_output_w=raw_props.get(PROP_OUTPUT_HOME_POWER),
        battery_charge_w=raw_props.get(PROP_OUTPUT_PACK_POWER),
        battery_discharge_w=raw_props.get(PROP_PACK_INPUT_POWER),
        input_limit_w=in_limit,
        output_limit_w=out_limit,
        ac_mode=ac_mode,
        smart_mode=smart_mode,
        grid_reverse=raw_props.get(PROP_GRID_REVERSE),
        temperature_c=temp_c,
        rssi_dbm=raw_props.get(PROP_RSSI),
        fault_level=raw_props.get(PROP_FAULT_LEVEL),
        error=has_error,
        grid_connected=grid_conn,
        reverse_flow_active=rev_active,
        pass_through=pass_through,
        heating=heating,
        remain_out_time_min=raw_props.get(PROP_REMAIN_OUT_TIME),
        last_transaction_state=existing_state.last_transaction_state if existing_state else TRANSACTION_IDLE,
        last_transaction_detail=existing_state.last_transaction_detail if existing_state else None,
        pack_data=packs if packs else (existing_state.pack_data if existing_state else []),
        raw_properties=raw_props,
    )
