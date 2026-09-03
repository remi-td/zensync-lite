"""Pytest configuration and mock fixtures for Zendure Local tests."""

from __future__ import annotations

import asyncio
from typing import Any
import pytest
from aiohttp import web

MOCK_SF2400_REPORT = {
    "timestamp": 1749110672,
    "messageId": 100,
    "sn": "SF2400A10001",
    "version": 102,
    "product": "SolarFlow2400 AC",
    "properties": {
        "electricLevel": 85,
        "packState": 1,
        "solarInputPower": 450,
        "solarPower1": 250,
        "solarPower2": 200,
        "gridInputPower": 0,
        "outputHomePower": 150,
        "outputPackPower": 300,
        "packInputPower": 0,
        "remainOutTime": 180,
        "acMode": 1,
        "inputLimit": 800,
        "outputLimit": 600,
        "socSet": 90,
        "minSoc": 15,
        "smartMode": 1,
        "gridReverse": 0,
        "rssi": -62,
        "heatState": 0,
        "is_error": 0,
        "faultLevel": 0,
        "gridState": 1,
        "reverseState": 0,
        "hyperTmp": 28.5,
        "pass": 0,
    },
    "packData": [
        {
            "sn": "PACK001",
            "packType": 1,
            "socLevel": 85,
            "state": 1,
            "power": 300,
            "maxTemp": 2981,  # (2981 - 2731) / 10 = 25.0 C
            "totalVol": 48.2,
            "batcur": 62,     # 6.2 A
            "maxVol": 332,    # 3.32 V
            "minVol": 328,    # 3.28 V
            "softVersion": 101,
            "heatState": 0,
        }
    ],
}


class MockZendureServer:
    """Mock HTTP server simulating Zendure ZenSDK device endpoints."""

    def __init__(self) -> None:
        self.report_data = dict(MOCK_SF2400_REPORT)
        self.report_data["properties"] = dict(MOCK_SF2400_REPORT["properties"])
        self.last_write: dict[str, Any] | None = None
        self.write_history: list[dict[str, Any]] = []
        self.should_fail_report = False
        self.should_fail_write = False
        self.ignore_property_writes = False
        self.write_delay = 0.0
        self.app = web.Application()
        self.app.router.add_get("/properties/report", self.handle_report)
        self.app.router.add_post("/properties/write", self.handle_write)
        self.app.router.add_get("/rpc", self.handle_rpc)
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self.port: int = 0

    async def handle_report(self, request: web.Request) -> web.Response:
        if self.should_fail_report:
            return web.Response(status=500, text="Internal Device Error")
        return web.json_response(self.report_data)

    async def handle_write(self, request: web.Request) -> web.Response:
        if self.write_delay > 0:
            await asyncio.sleep(self.write_delay)
        payload = await request.json()
        self.last_write = payload
        self.write_history.append(payload)

        if self.should_fail_write:
            return web.Response(status=400, text="Invalid parameters")

        # Simulate applying properties to the device's state report
        if not self.ignore_property_writes and "properties" in payload and isinstance(payload["properties"], dict):
            for k, v in payload["properties"].items():
                self.report_data["properties"][k] = v

        return web.json_response({"code": 200, "success": True, "sn": payload.get("sn")})

    async def handle_rpc(self, request: web.Request) -> web.Response:
        method = request.query.get("method")
        if method == "HA.Mqtt.GetStatus":
            return web.json_response({"connected": True})
        return web.json_response({"result": True})

    async def start(self) -> None:
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        # Retrieve allocated random port
        self.port = self.site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()


@pytest.fixture
async def mock_zendure_server():
    """Start and yield mock Zendure server."""
    server = MockZendureServer()
    await server.start()
    try:
        yield server
    finally:
        await server.stop()
