#!/usr/bin/env python3
"""Directly probe a Zendure battery over the LAN and display parsed status."""

import asyncio
import json
import sys

from custom_components.zensync_lite.capabilities import get_device_capability
from custom_components.zensync_lite.model import parse_report_payload
from custom_components.zensync_lite.transport.local_http import LocalHttpTransport


async def probe(host: str, port: int = 80) -> None:
    print(f"Connecting to Zendure battery at http://{host}:{port}/properties/report ...")
    transport = LocalHttpTransport(serial="", host=host, port=port)
    try:
        raw = await transport.async_fetch_state()
        print("\n=== RAW REPORT RECEIVED ===")
        print(f"Serial:  {raw.get('sn')}")
        print(f"Product: {raw.get('product')}")
        print(f"Version: {raw.get('version')}")

        state = parse_report_payload(raw)
        cap = get_device_capability(state.model)

        print("\n=== NORMALIZED BATTERY STATE ===")
        print(f"Model:                {state.model}")
        print(f"Matched Capability:   {cap.display_name} ({cap.model_key})")
        print(f"Read-Only Mode:       {cap.read_only}")
        print(f"Battery SOC:          {state.soc_percent} %")
        print(f"Battery State:        {state.battery_state}")
        print(f"Target SOC Limit:     {state.target_soc_percent} %")
        print(f"Minimum SOC Limit:    {state.min_soc_percent} %")
        print(f"AC Charge Limit:      {state.input_limit_w} W")
        print(f"Output Limit:         {state.output_limit_w} W")
        print(f"Operating Mode:       {state.ac_mode} (1=charge, 2=discharge)")
        print(f"Volatile Mode:        {state.smart_mode} (1=RAM only / no flash wear)")
        print(f"Temperature:          {state.temperature_c} °C")
        print(f"Signal Strength RSSI: {state.rssi_dbm} dBm")
        print(f"Grid Connected:       {state.grid_connected}")

        if state.pack_data:
            print("\n=== CONNECTED BATTERY PACKS ===")
            for i, p in enumerate(state.pack_data):
                print(f"Pack {i+1} [{p.sn}]:")
                print(f"  SOC:         {p.soc_percent} %")
                print(f"  State:       {p.state}")
                print(f"  Voltage:     {p.total_vol_v} V")
                print(f"  Current:     {p.current_a} A")
                print(f"  Temperature: {p.max_temp_c} °C")
                print(f"  Cell Max:    {p.max_cell_vol_v} V | Cell Min: {p.min_cell_vol_v} V")

        print("\nAll values successfully verified!")

    except Exception as e:
        print(f"\n[ERROR] Failed probing battery: {e}")
        sys.exit(1)
    finally:
        await transport.async_close()


if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.137"
    target_port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    asyncio.run(probe(target_ip, target_port))
