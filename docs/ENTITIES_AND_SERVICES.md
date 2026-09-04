# ZenSync Lite: Entities & Actions Reference

Complete catalog of all entities, device classes, state mappings, and actions exposed by `zensync_lite`.

---

## 1. Sensors (`sensor.*`)

### Primary Telemetry
| Entity Key | Name | Unit | Device Class | Description |
|---|---|---|---|---|
| `electric_level` | Battery SOC | `%` | `battery` | Current state of charge across all connected battery packs. |
| `battery_state` | Battery State | — | `enum` | Operational state: `standby`, `charging`, `discharging`, or `unknown`. |
| `solar_input_power` | Solar Input Power | `W` | `power` | Total real-time solar input power from all MPPT channels. |
| `home_output_power` | Home Output Power | `W` | `power` | Real-time AC power flowing from inverter into home circuits. |
| `battery_charge_power` | Battery Charge Power | `W` | `power` | Real-time power flowing into the battery cells (`outputPackPower`). |
| `battery_discharge_power`| Battery Discharge Power| `W` | `power` | Real-time power discharging from battery cells (`packInputPower`). |
| `grid_input_power` | Grid Input Power | `W` | `power` | AC charging power imported from the home grid into the inverter. |
| `temperature` | Inverter Temperature | `°C` | `temperature` | Internal inverter temperature normalized from `hyperTmp` (0.1K). |
| `rssi` | Signal Strength | `dBm` | `signal_strength`| Wi-Fi signal strength of the battery controller. |

### Limit & Diagnostics Sensors
| Entity Key | Name | Unit | Category | Description |
|---|---|---|---|---|
| `target_soc` | Target SOC | `%` | `diagnostic` | Configured upper charging threshold (70%–100%). |
| `minimum_soc` | Minimum SOC | `%` | `diagnostic` | Configured lower discharge cutoff (0%–50%). |
| `ac_charge_limit` | AC Charge Limit | `W` | `diagnostic` | Configured maximum AC grid charging power. |
| `output_limit` | Output Limit | `W` | `diagnostic` | Configured maximum home output discharge power. |
| `active_transport` | Active Transport | — | `diagnostic` | Currently active transport protocol (`local_http`, `local_mqtt`, `cloud`). |
| `command_status` | Command Status | — | `diagnostic` | State of latest write transaction (`idle`, `queued`, `sent`, `confirmed`, `failed`, `timed_out`). |
| `command_detail` | Command Detail | — | `diagnostic` | Contextual error or confirmation message of latest transaction. |
| `last_seen` | Last Seen | ISO | `diagnostic` | Timestamp of most recent successful poll. |

### Per-PV Channel & Pack Sensors (Optional / Secondary)
- `solar_power_pv1` to `solar_power_pv6`: Individual solar string power (Watts).
- `pack_{sn}_soc`: Individual battery pack SOC (%).
- `pack_{sn}_temp`: Individual battery pack temperature (°C).
- `pack_{sn}_voltage`: Pack bus voltage (Volts).
- `pack_{sn}_current`: Pack current (Amperes).
- `pack_{sn}_cell_max_v` / `cell_min_v`: Highest and lowest cell voltages within the pack.

---

## 2. Binary Sensors (`binary_sensor.*`)

| Entity Key | Name | Device Class | Description |
|---|---|---|---|
| `device_available` | Device Available | `connectivity` | True when the battery responds to LAN polls. |
| `stale_data` | Data Stale | `problem` | True when 3 consecutive poll cycles fail. State values are preserved. |
| `error_present` | Error Present | `problem` | True if the firmware reports internal hardware or communication faults. |
| `grid_connected` | Grid Connected | `connectivity` | True when the inverter AC grid relay is closed and synchronized. |
| `reverse_flow_active` | Reverse Flow Active| — | True when AC grid power reverse flow is active. |
| `local_api_available` | Local API Available | `connectivity` | True when HTTP port 80 responds to API calls. |
| `heating_active` | Heating Active | `heat` | True when internal low-temperature battery heating is active. |

---

## 3. Controls

### Numbers (`number.*`)
| Entity Key | Name | Unit | Range | Step | Description |
|---|---|---|---|---|---|
| `charge_limit_setting` | Charge Limit | `W` | 0 – `chargeMaxLimit` (W) | 10 W | Maximum allowable AC grid charging power. |
| `output_limit_setting` | Output Limit | `W` | 0 – `inverseMaxPower` (W)| 10 W | Maximum allowable home output discharge power. |
| `target_soc_setting` | Target SOC Limit | `%` | 70% – 100% | 1% | Upper charging threshold before charging stops. |
| `minimum_soc_setting` | Minimum SOC Limit| `%` | 0% – 50% | 1% | Discharge cutoff threshold to preserve battery health. |

### Selects (`select.*`)
| Entity Key | Name | Options | Description |
|---|---|---|---|
| `operating_mode` | Operating Mode | `charge` (1), `discharge` (2) | Sets the inverter operational mode. |

### Switches (`switch.*`)
| Entity Key | Name | Category | Description |
|---|---|---|---|
| `volatile_write_mode` | Volatile Write Mode | `config` | When ON (`smartMode: 1`), power and mode writes are held in volatile MCU RAM, eliminating flash wear. |
| `grid_reverse` | Grid Reverse Flow | `config` | Toggle reverse power flow behavior. |

### Buttons (`button.*`)
| Entity Key | Name | Category | Description |
|---|---|---|---|
| `refresh_now` | Refresh Now | `diagnostic` | Triggers an immediate state poll from the battery. |
| `rediscover_endpoint`| Rediscover Endpoint| `diagnostic`| Performs an mDNS query to locate the battery if its IP address changed. |
| `test_write_path` | Test Write Path | `diagnostic` | Sends a safe no-op write (`smartMode: 1`) to verify local write permissions. |

---

## 4. Integration Actions / Services

### `zensync_lite.set_charge_limit`
Sets the AC grid charging power limit.
```yaml
action: zensync_lite.set_charge_limit
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
data:
  limit: 800  # Watts
```

### `zensync_lite.set_output_limit`
Sets the home output discharge power limit.
```yaml
action: zensync_lite.set_output_limit
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
data:
  limit: 300  # Watts
```

### `zensync_lite.set_mode`
Switches inverter operating mode.
```yaml
action: zensync_lite.set_mode
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
data:
  mode: "charge"  # or "discharge"
```

### `zensync_lite.set_soc_limits`
Configures battery SOC operating bounds simultaneously.
```yaml
action: zensync_lite.set_soc_limits
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
data:
  min_soc: 15     # %
  target_soc: 95  # %
```

### `zensync_lite.stop_output`
Immediately stops home discharge by setting the output limit to 0W.
```yaml
action: zensync_lite.stop_output
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
```

### `zensync_lite.refresh`
Requests an immediate data refresh from the battery.
```yaml
action: zensync_lite.refresh
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
```

### `zensync_lite.rediscover`
Initiates background mDNS rediscovery to resolve updated device IP endpoints.
```yaml
action: zensync_lite.rediscover
target:
  device_id: 1e66e7c0507884301d75c748a97f16bf
```
