# Zendure Local Battery Control: Solar Surplus Management Guide

This guide explains how to dynamically balance home solar surplus and home load deficits using the included **Surplus Controller Blueprint**.

---

## 1. The Strategy: Integration vs Automations

```
+--------------------------+          +--------------------------+
| Home Grid Meter          |          | Solar PV Inverter        |
| (P1 Port / Shelly 3EM)   |          | (Current Solar Production|
+--------------------------+          +--------------------------+
             \                                      /
              \                                    /
               v                                  v
        +------------------------------------------------+
        | Home Assistant Automation / Surplus Blueprint   |
        | - Calculates excess solar (Surplus)            |
        | - Adjusts charge/discharge power limits        |
        | - Enforces deadbands and rate-limiting         |
        +------------------------------------------------+
                               |
                               v
        +------------------------------------------------+
        | zendure_local Integration                      |
        | - Executes writes in RAM (smartMode: 1)        |
        | - Protects battery health with SOC cutoffs     |
        | - Confirms state transition on physical device |
        +------------------------------------------------+
```

Because `zendure_local` does not embed an internal energy manager, you are free to customize your energy strategy using standard Home Assistant tools:
- **Solar Surplus Charging**: Store excess rooftop generation instead of exporting to grid at low feed-in tariffs.
- **Peak Shaving**: Discharge battery during high household consumption.
- **Dynamic Tariff Arbitrage**: Charge from grid during negative or cheap tariff hours (Nordpool, Tibber) and discharge during peak prices.

---

## 2. The Surplus Controller Blueprint

The blueprint is located at [`blueprints/automation/surplus_controller.yaml`](file:///Users/remi.turpaud/Code/zndure-ha-lite/blueprints/automation/surplus_controller.yaml).

### How to Import
1. In Home Assistant, navigate to **Settings > Automations & Scenes > Blueprints**.
2. Click **Add Blueprint** (bottom right).
3. If using the local sandbox or manually copied installation, select **Zendure Solar Surplus Controller** from the list.
4. Click **Create Automation**.

---

## 3. Blueprint Configuration Parameters

### 3.1 Grid Meter & Sign Convention
- **Grid Power Sensor**: Select the entity measuring home grid exchange (e.g. `sensor.power_meter_active_power` or `sensor.p1_electricity_net`).
- **Power Sign Convention**:
  - **Positive = Export, Negative = Import**: Standard convention for many solar inverters, Enphase, and DSMR P1 integrations.
  - **Positive = Import, Negative = Export**: Standard convention for Shelly 3EM, Tibber Pulse, and IoTaWatt.

### 3.2 Battery Entities
- **Battery SOC Sensor**: Select `sensor.zendure_solarflow2400ac_hec4nencn490106_battery_soc`.
- **Charge Limit Entity**: Select `number.zendure_solarflow2400ac_hec4nencn490106_charge_limit`.
- **Output Limit Entity**: Select `number.zendure_solarflow2400ac_hec4nencn490106_output_limit`.
- **Operating Mode Entity**: Select `select.zendure_solarflow2400ac_hec4nencn490106_operating_mode`.

### 3.3 Power Deadbands & Safety Bounds
- **Deadband (Watts)** (Default: `50 W`):
  Small grid fluctuations within this band are ignored. This prevents the inverter relays from hunting or re-adjusting unnecessarily.
- **Max Grid Charge Power (Watts)** (Default: `1200 W`):
  Maximum rate at which the battery charges from excess solar.
- **Max Discharge Power (Watts)** (Default: `800 W`):
  Maximum rate at which the battery discharges into home circuits to cover deficits.
- **Target / Max SOC Limit (%)** (Default: `95%`):
  When battery reaches this SOC, charging stops to prevent cell stress.
- **Minimum SOC Cutoff (%)** (Default: `15%`):
  When battery drops below this SOC, discharging stops to protect battery longevity.

---

## 4. Flash Wear Immunity

When the automation updates the `inputLimit` or `outputLimit` numbers:
- `zendure_local` automatically writes to volatile MCU memory (`smartMode: 1`).
- The automation can adjust limits every 15–30 seconds safely without degrading the battery's flash memory.

---

## 5. Example Advanced Automations

### Dynamic Tariff Grid Fast-Charging (e.g. Tibber / Nordpool)
You can create a simple automation to force-charge the battery when electricity price is negative or below your threshold:

```yaml
alias: "Battery: Charge on Negative Electricity Tariff"
trigger:
  - platform: numeric_state
    entity_id: sensor.electricity_price
    below: 0.00  # Currency / kWh
condition:
  - condition: numeric_state
    entity_id: sensor.zendure_solarflow2400ac_hec4nencn490106_battery_soc
    below: 90
action:
  - action: zendure_local.set_mode
    target:
      device_id: 1e66e7c0507884301d75c748a97f16bf
    data:
      mode: "charge"
  - action: zendure_local.set_charge_limit
    target:
      device_id: 1e66e7c0507884301d75c748a97f16bf
    data:
      limit: 2000
```
