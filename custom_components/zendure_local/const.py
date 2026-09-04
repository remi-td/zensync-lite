"""Constants for the Zendure Local Battery Control integration."""

from __future__ import annotations

DOMAIN = "zendure_local"
NAME = "Zendure Local Battery Control"
MANUFACTURER = "Zendure"

# Network & Timing defaults
DEFAULT_PORT = 80
DEFAULT_TIMEOUT_CONNECT = 3.0  # seconds
DEFAULT_TIMEOUT_READ = 5.0     # seconds
DEFAULT_MAX_RETRIES = 2
DEFAULT_POLL_INTERVAL = 10     # seconds
STALE_THRESHOLD_INTERVALS = 3  # missed intervals before marking stale
CONFIRMATION_DELAY = 1.0       # seconds initial delay before readback check
CONFIRMATION_RETRIES = 3       # max readback confirmation attempts
CONFIRMATION_RETRY_DELAY = 1.5 # delay between confirmation attempts

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL = "serial"
CONF_MODEL = "model"
CONF_TRANSPORT = "transport"
CONF_VOLATILE_WRITES = "volatile_writes"
CONF_ENABLE_LOCAL_MQTT = "enable_local_mqtt"
CONF_ENABLE_CLOUD = "enable_cloud"

# Transports
TRANSPORT_LOCAL_HTTP = "local_http"
TRANSPORT_LOCAL_MQTT = "local_mqtt"
TRANSPORT_CLOUD = "cloud"

# Transaction states
TRANSACTION_IDLE = "idle"
TRANSACTION_QUEUED = "queued"
TRANSACTION_SENT = "sent"
TRANSACTION_CONFIRMED = "confirmed"
TRANSACTION_FAILED = "failed"
TRANSACTION_TIMED_OUT = "timed_out"

# Battery Operational States
STATE_STANDBY = "standby"
STATE_CHARGING = "charging"
STATE_DISCHARGING = "discharging"
STATE_UNKNOWN = "unknown"

MAP_PACK_STATE = {
    0: STATE_STANDBY,
    1: STATE_CHARGING,
    2: STATE_DISCHARGING,
}

# AC Inverter Modes
AC_MODE_CHARGE = 1
AC_MODE_DISCHARGE = 2

MODE_CHARGE_STR = "charge"
MODE_DISCHARGE_STR = "discharge"

MAP_AC_MODE_TO_STR = {
    AC_MODE_CHARGE: MODE_CHARGE_STR,
    AC_MODE_DISCHARGE: MODE_DISCHARGE_STR,
}

MAP_STR_TO_AC_MODE = {
    MODE_CHARGE_STR: AC_MODE_CHARGE,
    MODE_DISCHARGE_STR: AC_MODE_DISCHARGE,
}

# ZenSDK Raw Properties
PROP_ELECTRIC_LEVEL = "electricLevel"
PROP_PACK_STATE = "packState"
PROP_SOLAR_INPUT_POWER = "solarInputPower"
PROP_GRID_INPUT_POWER = "gridInputPower"
PROP_OUTPUT_HOME_POWER = "outputHomePower"
PROP_OUTPUT_PACK_POWER = "outputPackPower"
PROP_PACK_INPUT_POWER = "packInputPower"
PROP_REMAIN_OUT_TIME = "remainOutTime"
PROP_AC_MODE = "acMode"
PROP_INPUT_LIMIT = "inputLimit"
PROP_OUTPUT_LIMIT = "outputLimit"
PROP_SOC_SET = "socSet"
PROP_MIN_SOC = "minSoc"
PROP_SMART_MODE = "smartMode"
PROP_GRID_REVERSE = "gridReverse"
PROP_RSSI = "rssi"
PROP_HEAT_STATE = "heatState"
PROP_IS_ERROR = "is_error"
PROP_FAULT_LEVEL = "faultLevel"
PROP_DRY_NODE_STATE = "dryNodeState"
PROP_CHARGE_MAX_LIMIT = "chargeMaxLimit"
PROP_INVERSE_MAX_POWER = "inverseMaxPower"
PROP_GRID_STATE = "gridState"
PROP_REVERSE_STATE = "reverseState"
PROP_HYPER_TMP = "hyperTmp"
PROP_PASS = "pass"

# Services
SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
SERVICE_SET_OUTPUT_LIMIT = "set_output_limit"
SERVICE_SET_MODE = "set_mode"
SERVICE_SET_SOC_LIMITS = "set_soc_limits"
SERVICE_STOP_OUTPUT = "stop_output"
SERVICE_REFRESH = "refresh"
SERVICE_REDISCOVER = "rediscover"

ATTR_LIMIT = "limit"
ATTR_MODE = "mode"
ATTR_MIN_SOC = "min_soc"
ATTR_TARGET_SOC = "target_soc"
ATTR_SUCCESS = "success"
ATTR_TRANSACTION_STATE = "transaction_state"
