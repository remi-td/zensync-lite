# Zendure Local Battery Control: Setup & Installation Guide

This guide walks through configuring your Zendure battery, installing the integration in Home Assistant, and testing connectivity.

---

## 1. Device Preparation & Network Setup

### 1.1 Firmware & HEMS Mode (EN 18031 Compliance)
On newer Zendure firmware adhering to European cybersecurity standard EN 18031, local HTTP API access is disabled by default. You must enable **HEMS / Local API Mode** in the official Zendure mobile app:

1. Open the **Zendure App** on your smartphone.
2. Select your battery / inverter system.
3. Open **Settings** (gear icon) > **System Settings**.
4. Enable **HEMS Mode** (or **Local API / Third-Party Energy Management**).
5. **Completely exit/kill the Zendure App**.
   > [!IMPORTANT]
   > Some firmware builds keep the local port blocked while the official app maintains an active Bluetooth or cloud connection to the unit. Force-closing the mobile app ensures the local HTTP server opens on port 80.

### 1.2 Router DHCP Reservation
We recommend assigning a **static DHCP reservation** to your Zendure battery in your home router (e.g. `192.168.1.137`). This ensures the IP address remains constant across router restarts.

---

## 2. Installation Methods

### Method A: Manual Installation (Standard Home Assistant)

1. Navigate to your Home Assistant configuration directory (`/config`).
2. If `custom_components` does not exist, create it:
   ```bash
   mkdir -p custom_components
   ```
3. Copy the `custom_components/zendure_local` directory from this repository into `/config/custom_components/zendure_local`.
4. Copy the surplus controller blueprint:
   ```bash
   mkdir -p /config/blueprints/automation/zendure_local
   cp blueprints/automation/surplus_controller.yaml /config/blueprints/automation/zendure_local/
   ```
5. Restart Home Assistant via **Settings > System > Restart**.

---

### Method B: Testing via the Local Docker Sandbox

This repository includes a turnkey local Docker sandbox for quick evaluation without touching your production Home Assistant server.

1. Ensure Docker Desktop is installed and running on your computer.
2. Start the sandbox:
   ```bash
   ./ha_sandbox/start.sh
   ```
3. Open your browser to **[http://localhost:8123](http://localhost:8123)**.
4. Complete initial onboarding (choose any username/password).
5. The integration and blueprint are already mounted and ready to use!

To stop the sandbox:
```bash
./ha_sandbox/stop.sh
```

---

## 3. Adding the Integration in Home Assistant

### Option 1: Automatic Discovery (mDNS / Zeroconf)
If your Zendure battery and Home Assistant are on the same subnet, Home Assistant will detect the device automatically under **Settings > Devices & Services > Discovered**.
Click **Configure** to finish setup.

### Option 2: Manual IP Configuration
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** (bottom right).
3. Search for **Zendure Local Battery Control**.
4. Enter:
   - **Host**: Your battery IP (e.g. `192.168.1.137`)
   - **Port**: `80` (default)
5. Click **Submit**.

Home Assistant probes the battery, detects the model (e.g. `SolarFlow 2400 AC+`) and hardware serial number, and registers all sensors and controls.

---

## 4. Integration Options

You can adjust runtime parameters at any time:
1. Go to **Settings > Devices & Services**.
2. Find **Zendure Local Battery Control** and click **Configure**.
3. Available options:
   - **Poll Interval (seconds)**: Frequency of state polling (default: `10` seconds, range 5–60s).
   - **Volatile Writes (`smartMode`)**: When enabled (default: `True`), automation writes modify MCU RAM only, completely eliminating flash memory wear.

---

## 5. Troubleshooting & Diagnostics

### Battery Not Responding on Port 80
- Verify the battery is powered on and connected to your Wi-Fi (blue Wi-Fi indicator solid).
- Check that the battery IP responds to ping:
  ```bash
  ping 192.168.1.137
  ```
- Run the built-in diagnostic probe tool:
  ```bash
  python3 scripts/probe_battery.py 192.168.1.137
  ```
- Verify HEMS Mode is enabled in the Zendure app and force-close the Zendure mobile app.

### Data Stale Warning (Binary Sensor: Data Stale is ON)
- Triggered automatically if Home Assistant misses 3 consecutive poll intervals.
- The integration preserves your last known SOC and power limits; it does not clear values to zero.
- Once communication restores, the warning clears automatically.

### Battery Changed IP Address
- Click the **Rediscover Endpoint** button on the device page, or call the `zendure_local.rediscover` action.
- The integration queries mDNS for the device serial number and updates the IP address dynamically without creating duplicate entities.
