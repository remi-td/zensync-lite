# ZenSync Lite

<p align="center">
  <img src="https://raw.githubusercontent.com/home-assistant/brands/master/core_integrations/battery/icon.png" alt="ZenSync Lite Logo" width="100">
</p>

<p align="center">
  <strong>Fast, lean, and local-first Home Assistant integration for Zendure battery systems (SolarFlow series, Hyper 2000).</strong><br>
  <em>Reliable local control without cloud dependency, race conditions, or flash wear.</em>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/remi-td/zensync-lite/releases"><img src="https://img.shields.io/github/v/release/remi-td/zensync-lite?style=for-the-badge&color=34D399" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License"></a>
  <a href="docs/ARCHITECTURE.md"><img src="https://img.shields.io/badge/Hardware-SolarFlow%202400%20AC%2B%20Verified-brightgreen.svg?style=for-the-badge" alt="Hardware Verified"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=remi-td&repository=zensync-lite&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.">
  </a>
</p>

---

## ⚡ The ZenSync Philosophy

Unlike monolithic integrations that embed an inflexible energy manager inside the integration itself, **ZenSync Lite** follows the Unix philosophy: **do one job exceptionally well**.

> **Maintain a true, real-time model of your Zendure battery over your local network, and provide safe, explicit, transactional controls for charging, discharging, power limits, and operating modes.**

Your energy strategy (dynamic tariffs, solar forecasts, home surplus balancing, peak shaving) belongs where it is most flexible: in **Home Assistant Automations, Scripts, and Blueprints**.

---

## 🌟 Key Features

- ⚡ **100% Local HTTP First**: Communicates directly with the battery's embedded ZenSDK server (`GET /properties/report`, `POST /properties/write`). Blazing sub-40ms response times, zero cloud lag, and 100% functional during internet outages.
- 🛡️ **Zero Flash Wear (`smartMode: 1`)**: Fast automation writes (e.g. solar surplus regulation every 10–30s) write directly to volatile MCU RAM by default, completely eliminating flash memory wear and premature hardware failure.
- 🔒 **Readback Write Confirmation**: Control entities reflect confirmed hardware truth from readback verification, never optimistic assumptions. Features a multi-attempt grace window to accommodate physical relay switching times.
- 🎯 **Dynamic Hardware Limit Clamping**: Sliders automatically adapt their upper bounds to physical inverter ratings reported by the unit (`chargeMaxLimit: 2400W`, `inverseMaxPower: 900W`).
- 🔢 **Intelligent Calibration**: Seamlessly handles tenths-of-a-percent SOC scaling (`socSet: 1000` = 100%), centivolts, signed 16-bit 2's complement currents, and Kelvin temperatures.
- ☀️ **Turnkey Surplus Blueprint**: Ships with a ready-to-use solar surplus controller blueprint for instant balancing with P1 meters, Shelly 3EM, or solar sensors.
- 🔄 **Stale State Preservation**: Temporary Wi-Fi dropouts do not wipe out your SOC or settings. Data is marked stale only after 3 consecutive missed polls, preserving last known values.
- 👥 **Multi-Device Collision Proof**: Unique IDs strictly use hardware serial numbers (`zensync_lite_<serial>_<key>`), allowing multiple inverters on the same network without conflict.

---

## 📋 Supported Hardware Matrix

| Model | Transport | Max Charge | Max Discharge | Status |
|---|---|---|---|---|
| **SolarFlow 2400 AC+** | Local HTTP | 3200 W (2400 W AC) | 2400 W (900 W AC) | ✅ **Hardware Verified in Live Testing** |
| **SolarFlow 2400 AC** | Local HTTP | 2400 W | 2400 W | ✅ Supported |
| **SolarFlow 1600 AC+** | Local HTTP | 1600 W | 1200 W | ✅ Supported |
| **SolarFlow 800 / 800 Plus / 800 Pro** | Local HTTP | 800 W | 800 W | ✅ Supported |
| **SolarFlow 2400 Pro** | Local HTTP | 3200 W | 2400 W | ✅ Supported |
| **Hyper 2000** *(ZenSDK firmware)* | Local HTTP | 2400 W | 2400 W | ✅ Supported |
| **SmartMeter 3CT** | Local HTTP | — | — | 📊 Telemetry Only (Read-Only) |

---

## 🚀 Installation

### Option 1: HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant.
2. Click the **My Home Assistant** button below to open the repository directly:

   [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=remi-td&repository=zensync-lite&category=integration)

   *Or manually:* In HACS, go to **Integrations > Custom repositories**, add `https://github.com/remi-td/zensync-lite`, and select category **Integration**.
3. Click **Download**, then restart Home Assistant.

### Option 2: Manual Installation

1. Copy the [`custom_components/zensync_lite`](custom_components/zensync_lite) directory into your Home Assistant `/config/custom_components/zensync_lite` folder.
2. *(Optional)* Copy the blueprint [`blueprints/automation/surplus_controller.yaml`](blueprints/automation/surplus_controller.yaml) into `/config/blueprints/automation/zensync_lite/`.
3. Restart Home Assistant.

### Option 3: Local Docker Sandbox

This repository includes a turnkey Docker sandbox for evaluation without touching your production Home Assistant server:

```bash
# Start sandbox on http://localhost:8123
./ha_sandbox/start.sh

# Stop sandbox
./ha_sandbox/stop.sh
```

---

## ⚙️ Device Preparation & Network Setup

### 1. Enable HEMS Mode (EN 18031 Compliance)
On modern Zendure firmware adhering to EU cybersecurity regulations (EN 18031), local HTTP API access is disabled by default:
1. Open the official **Zendure App** on your smartphone.
2. Select your device > **Settings** (gear icon) > **System Settings**.
3. Enable **HEMS Mode** (or **Local API / Third-Party Energy Management**).
4. **Force-close the Zendure mobile app**.
   > [!IMPORTANT]
   > Some firmware builds keep local port 80 closed while the mobile app maintains an active Bluetooth or cloud session. Closing the app allows the local HTTP server to accept LAN connections.

### 2. Router Static DHCP Reservation
Assign a static DHCP lease in your home router (e.g. `192.168.1.137`) so the battery retains its IP address across reboots.

---

## 🔧 Configuration in Home Assistant

1. In Home Assistant, go to **Settings > Devices & Services > Add Integration**.
2. Search for **ZenSync Lite**.
3. Enter:
   - **Host**: Your battery's local IP address (e.g. `192.168.1.137`)
   - **Port**: `80` (default)
4. Click **Submit**. ZenSync Lite automatically queries the device, detects its serial number and model, and registers all entities.

### Options Flow
Click **Configure** on the integration card to customize:
- **Poll Interval**: 5 to 60 seconds (default: `10` seconds).
- **Volatile Writes (`smartMode`)**: Enable/disable RAM-only writes (default: `True`).

---

## 📊 Entities & Controls

### Telemetry Sensors
- **Battery SOC** (`%`)
- **Battery State** (`standby`, `charging`, `discharging`, `unknown`)
- **Solar Input Power** (`W`)
- **Home Output Power** (`W`)
- **Battery Charge Power** (`W`)
- **Battery Discharge Power** (`W`)
- **Grid Input Power** (`W`)
- **Device Temperature** (`°C`, normalized from 0.1K)
- **Wi-Fi Signal Strength (RSSI)** (`dBm`)
- *Per-pack sensors (SOC, voltage, current, individual cell min/max voltages)*
- *Per-PV channel sensors (PV1 to PV6 Watts)*

### Binary Sensors
- **Device Available** (LAN connectivity)
- **Data Stale** (tripped after 3 consecutive missed poll intervals)
- **Error Present** (internal hardware fault flags)
- **Grid Connected** (AC synchronization relay state)
- **Reverse Flow Active** (grid feed-in state)
- **Local API Available** (port 80 health)

### Controls
- **Charge Limit** (`number.charge_limit`, 0 to max W)
- **Output Limit** (`number.output_limit`, 0 to max W)
- **Target SOC Limit** (`number.target_soc_limit`, 70% to 100%)
- **Minimum SOC Limit** (`number.minimum_soc_limit`, 0% to 50%)
- **Operating Mode** (`select.operating_mode`: `charge`, `discharge`)
- **Volatile Write Mode** (`switch.volatile_write_mode`)
- **Refresh Now** (`button.refresh_now`)
- **Rediscover Endpoint** (`button.rediscover_endpoint`)

---

## 🛠️ Actions / Services

ZenSync Lite exposes explicit action services for reliable automations:

```yaml
# Set AC charging limit
action: zensync_lite.set_charge_limit
target:
  device_id: <DEVICE_ID>
data:
  limit: 1200

# Set home discharge limit
action: zensync_lite.set_output_limit
target:
  device_id: <DEVICE_ID>
data:
  limit: 600

# Switch mode (charge / discharge)
action: zensync_lite.set_mode
target:
  device_id: <DEVICE_ID>
data:
  mode: "charge"

# Update SOC bounds
action: zensync_lite.set_soc_limits
target:
  device_id: <DEVICE_ID>
data:
  min_soc: 15
  target_soc: 95

# Stop home output immediately
action: zensync_lite.stop_output
target:
  device_id: <DEVICE_ID>
```

---

## ☀️ Solar Surplus Controller Blueprint

ZenSync Lite includes a solar surplus automation blueprint (`blueprints/automation/surplus_controller.yaml`).

### Features:
- **Optional Moving Average Filter**: Smooths out choppy solar data and high-frequency appliance spikes (e.g. induction cooktop pulses, passing clouds) using an optional 30s–60s rolling average sensor.
- **Update Cooldown Rate-Limiting**: Configurable pause between inverter writes (default `15s`) to protect relay contacts and give MCU control loops time to settle.
- **Minimum Step Hysteresis**: Prevents micro-adjustments by only writing if target power changes by at least `30W`.
- **Zero-Crossing Deadband**: Ignores small grid fluctuations around 0W (default `50W`) to prevent rapid flipping between charge and discharge.
- **SOC Protection Caps**: Enforces user-configured minimum SOC discharge cutoffs and target SOC charge caps.
- **100% Opt-Out Support**: Filter window, cooldown, and step thresholds can all be set to `0` for instantaneous, raw reactive tracking.

See [**docs/SURPLUS_MANAGEMENT.md**](docs/SURPLUS_MANAGEMENT.md) for full configuration details and step-by-step filter helper setup.

---

## 📚 In-Depth Documentation

- [**Architecture & Safety Design**](docs/ARCHITECTURE.md): ZenSDK local API details, memory safety, write serialization, and conversion formulas.
- [**Setup & Installation Guide**](docs/SETUP_GUIDE.md): Detailed installation walkthrough, EN 18031 guide, and network troubleshooting.
- [**Entities & Services Reference**](docs/ENTITIES_AND_SERVICES.md): Complete catalog of entity keys, device classes, and action schemas.
- [**Solar Surplus Management Guide**](docs/SURPLUS_MANAGEMENT.md): Step-by-step blueprint setup and advanced tariff automation examples.

---

## 🧪 Development & Testing

Run the full automated test suite:

```bash
# Create virtual environment & install requirements
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt

# Run pytest
pytest tests/ -v
```

Probe physical battery telemetry directly:

```bash
python3 scripts/probe_battery.py <BATTERY_IP>
```

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
