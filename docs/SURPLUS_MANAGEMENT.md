# ZenSync Lite: Solar Surplus Management & Signal Filtering Guide

This guide explains how to dynamically balance home solar surplus and grid exchange using **ZenSync Lite** and the included **Solar Surplus Controller Blueprint**, with a deep dive on **signal filtering** to eliminate battery stress and relay hunting.

---

## 1. The Physical Problem: Grid & Solar "Choppiness"

When balancing a home battery against a smart meter (P1 port, Shelly 3EM, DSMR), raw power readings fluctuate rapidly on a second-by-second basis due to three physical factors:

```
           +-------------------------------------------------------------+
           |                   Sources of Grid Noise                     |
           +-------------------------------------------------------------+
                     /                      |                      \
                    /                       |                       \
                   v                        v                        v
          [Passing Clouds]         [Induction Cooktops]       [Smart Meter Rate]
       500W-2500W solar dips    Pulsing 0W <-> 2000W bursts   Reports updates
        lasting 5-20 seconds         every 2-4 seconds          every 1 second
```

### What Happens Without Filtering?
1. **Relay & MCU Thrashing**: The inverter receives up to 60 setpoint changes per minute.
2. **Control Loop Disruption**: Zendure SolarFlow firmware takes **1.5 to 2.5 seconds** to switch internal relays and settle its internal control loop. Sending commands every 1–2 seconds interrupts this settling process, causing false mismatch warnings and electrical stress on internal capacitors.
3. **Appliance "Chasing"**: When an induction cooktop pulses on for 3 seconds, the battery attempts to ramp discharge to 2000W; when it cycles off 2 seconds later, the battery attempts to drop back down. The battery is constantly chasing phantom transients.

---

## 2. Research: Meaningful Signal Filter Values

We analyzed how industry-leading smart battery controllers, inverters, and energy managers handle grid meter signal filtering:

| System / Controller | Filtering Mechanism | Typical Time Window | Primary Goal |
|---|---|---|---|
| **Tesla Powerwall / SolarEdge** | Low-pass filter on CT meter input | **20s – 30s** | Prevent relay hunting during cloud transients |
| **Victron ESS (Energy Storage)** | Rolling average on grid setpoint | **20s – 40s** | Stable zero-grid regulation without oscillation |
| **EVCC (EV Charge Controller)** | Rolling mean + enable/disable delays | **30s – 60s** (delays 1–3 min) | Smooth out cooktops and avoid rapid on/off cycling |
| **Zendure Smart CT Mode** | Internal firmware rate limiting | **7s – 10s** | Mechanical settling time for inverter stages |
| **Home Assistant Filter Helper** | `time_simple_moving_average` | **30s – 60s** | Community standard for domestic solar surplus |

### Recommended Filter Windows for Home Batteries:

- **30 to 45 seconds (Recommended Sweet Spot)**:
  - Completely eliminates induction cooktop PWM pulses (2–4s duty cycles) and micro-clouds.
  - Retains rapid agility when someone turns on a sustained load (kettle, oven, dishwasher).
- **60 to 90 seconds (Maximum Smoothing)**:
  - Best for locations with partly cloudy skies and rapid light/shadow transitions throughout the day.
- **0 seconds (Opt-Out / Instantaneous)**:
  - Disables filtering for users who prefer raw real-time reactive control.

---

## 3. How to Create a Moving Average Filter Helper in Home Assistant

Home Assistant includes a built-in **Filter Helper** designed specifically to calculate a rolling moving average from a source sensor.

### Method A: Through the Home Assistant UI (Recommended)

1. In Home Assistant, navigate to **Settings > Devices & Services > Helpers**.
2. Click **Create Helper** (bottom right).
3. Select **Filter**.
4. Configure:
   - **Name**: `Grid Power 45s Moving Average`
   - **Input Sensor**: Select your raw grid power sensor (e.g. `sensor.power_meter_active_power`).
   - **Filter Type**: **Time-based rolling mean** (or `Moving average`).
   - **Time Window**: `00:00:45` (45 seconds).
   - **Precision**: `0`
5. Click **Submit**.

---

### Method B: Via YAML (`configuration.yaml`)

Add the following block to your `configuration.yaml` and restart Home Assistant:

```yaml
sensor:
  - platform: filter
    name: "Grid Power 45s Moving Average"
    entity_id: sensor.power_meter_active_power  # Replace with your meter sensor
    filters:
      - filter: time_simple_moving_average
        window_size: "00:00:45"
        precision: 0
```

---

## 4. The ZenSync Lite Blueprint: Multi-Layer Stabilization

The included blueprint ([`blueprints/automation/surplus_controller.yaml`](../blueprints/automation/surplus_controller.yaml)) provides a comprehensive 4-layer stabilization system:

```
Raw Grid Sensor (1 Hz)
         |
         v
[Layer 1: Moving Average Filter]  --> Smooths out cooktops and clouds over 45s
         |
         v
[Layer 2: Step Hysteresis]        --> Ignores power drifts smaller than 30W
         |
         v
[Layer 3: Mode Settle Check]      --> Confirms sustained surplus/deficit before mode flip
         |
         v
[Layer 4: Update Cooldown]        --> Enforces minimum 15s between inverter writes
         |
         v
Physical Zendure Inverter (Zero Flash Wear, Confirmed Write)
```

### Blueprint Parameters:

1. **`moving_average_sensor` (Optional Filter Sensor)**:
   - Point to your newly created `sensor.grid_power_45s_moving_average`.
   - If left blank, the automation uses the raw grid power sensor directly.
2. **`update_interval_seconds` (Minimum Cooldown, Default: `15s`)**:
   - Enforces a minimum pause between consecutive write commands.
   - Set to `0` to disable cooldown and react on every update.
3. **`min_change_watts` (Step Hysteresis, Default: `30W`)**:
   - Only updates battery limits if the target power differs from the active limit by at least 30W.
   - Set to `0` to disable and adjust on any change.
4. **`deadband_watts` (Zero-Crossing Deadband, Default: `50W`)**:
   - Prevents direction hunting when home consumption closely matches solar production near 0W.

---

## 5. Opting Out (Pure Reactive Mode)

If you prefer instantaneous, unfiltered control without smoothing:
- Leave **Moving Average Filter Sensor** blank.
- Set **Minimum Update Cooldown** to `0`.
- Set **Minimum Power Change Threshold** to `0`.

The automation will execute immediately upon every state change reported by your grid meter.
