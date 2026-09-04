"""Config flow for Zendure Local Battery Control."""

from __future__ import annotations

import logging
from typing import Any

try:
    import voluptuous as vol
    from homeassistant import config_entries
    try:
        from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
    except ImportError:
        try:
            from homeassistant.components.zeroconf import ZeroconfServiceInfo
        except ImportError:
            class ZeroconfServiceInfo:  # type: ignore
                host: str = ""
                port: int | None = None
                name: str = ""

    from homeassistant.const import CONF_HOST, CONF_PORT
    from homeassistant.core import callback
    try:
        from homeassistant.config_entries import ConfigFlowResult as FlowResult
    except ImportError:
        from homeassistant.data_entry_flow import FlowResult  # type: ignore
except ImportError:
    vol = type("vol", (), {"Schema": lambda s: s, "Optional": lambda k, **kw: k, "Required": lambda k, **kw: k, "All": lambda *a: a, "Range": lambda **kw: kw, "In": lambda a: a})  # type: ignore
    from .compat import (  # type: ignore[no-redef]
        CONF_HOST,
        CONF_PORT,
        FlowResult,
        ZeroconfServiceInfo,
        callback,
        config_entries,
    )

from .capabilities import get_device_capability
from .const import (
    CONF_MODEL,
    CONF_SERIAL,
    CONF_TRANSPORT,
    CONF_VOLATILE_WRITES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    TRANSPORT_LOCAL_HTTP,
)
from .transport.base import TransportConnectionError, TransportError, TransportTimeoutError
from .transport.local_http import LocalHttpTransport

_LOGGER = logging.getLogger(__name__)


class ZendureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zendure Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        super().__init__()
        self.context: dict[str, Any] = getattr(self, "context", {})
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_serial: str | None = None
        self._discovered_model: str | None = None

    async def async_step_zeroconf(
        self,
        discovery_info: ZeroconfServiceInfo,
    ) -> FlowResult:
        """Handle mDNS/zeroconf discovery for _zendure._tcp."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        service_name = discovery_info.name

        _LOGGER.info("Discovered Zendure mDNS service: %s at %s:%s", service_name, host, port)

        # Attempt to probe device and fetch real serial/model
        transport = LocalHttpTransport(serial="", host=host, port=port)
        try:
            report = await transport.async_fetch_state()
            serial = report.get("sn") or _extract_serial_from_name(service_name)
            model = report.get("product") or _extract_model_from_name(service_name)
        except Exception as err:
            _LOGGER.debug("Failed probing discovered endpoint %s:%s: %s", host, port, err)
            serial = _extract_serial_from_name(service_name)
            model = _extract_model_from_name(service_name)
        finally:
            await transport.async_close()

        if not serial:
            return self.async_abort(reason="unknown_device")

        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: host,
                CONF_PORT: port,
            }
        )

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_serial = serial
        self._discovered_model = model

        self.context["title_placeholders"] = {
            "name": f"{model} ({serial})",
            "host": host,
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Confirm zeroconf discovery setup."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Zendure {self._discovered_model} ({self._discovered_serial})",
                data={
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: self._discovered_port,
                    CONF_SERIAL: self._discovered_serial,
                    CONF_MODEL: self._discovered_model,
                    CONF_TRANSPORT: TRANSPORT_LOCAL_HTTP,
                    CONF_VOLATILE_WRITES: True,
                },
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "model": self._discovered_model or "SolarFlow",
                "serial": self._discovered_serial or "Unknown",
                "host": self._discovered_host or "",
            },
        )

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle manual local configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            serial = user_input.get(CONF_SERIAL, "").strip()
            model = user_input.get(CONF_MODEL, "").strip()

            transport = LocalHttpTransport(serial=serial, host=host, port=port)
            try:
                report = await transport.async_fetch_state()
                detected_serial = report.get("sn") or serial
                detected_model = report.get("product") or model or "SolarFlow"

                if not detected_serial:
                    errors["base"] = "missing_serial"
                else:
                    await self.async_set_unique_id(detected_serial)
                    self._abort_if_unique_id_configured(
                        updates={
                            CONF_HOST: host,
                            CONF_PORT: port,
                        }
                    )

                    return self.async_create_entry(
                        title=f"Zendure {detected_model} ({detected_serial})",
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_SERIAL: detected_serial,
                            CONF_MODEL: detected_model,
                            CONF_TRANSPORT: TRANSPORT_LOCAL_HTTP,
                            CONF_VOLATILE_WRITES: user_input.get(CONF_VOLATILE_WRITES, True),
                        },
                    )

            except TransportTimeoutError:
                errors["base"] = "timeout"
            except TransportConnectionError:
                errors["base"] = "cannot_connect"
            except TransportError as err:
                _LOGGER.error("Transport error connecting to Zendure: %s", err)
                errors["base"] = "hems_not_enabled"
            except Exception as err:
                _LOGGER.exception("Unexpected error in config flow: %s", err)
                errors["base"] = "unknown"
            finally:
                await transport.async_close()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SERIAL, default=""): str,
                vol.Optional(CONF_MODEL, default=""): str,
                vol.Optional(CONF_VOLATILE_WRITES, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow handler."""
        return ZendureOptionsFlow(config_entry)


class ZendureOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Zendure Local Battery Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_VOLATILE_WRITES,
                    default=self.config_entry.options.get(
                        CONF_VOLATILE_WRITES,
                        self.config_entry.data.get(CONF_VOLATILE_WRITES, True),
                    ),
                ): bool,
                vol.Optional(
                    "poll_interval",
                    default=self.config_entry.options.get(
                        "poll_interval",
                        DEFAULT_POLL_INTERVAL,
                    ),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


def _extract_serial_from_name(name: str) -> str:
    """Extract serial number from mDNS name format Zendure-<Model>-<Last12MAC/SN>."""
    clean = name.replace("._zendure._tcp.local.", "").replace("._zendure._tcp.", "")
    parts = clean.split("-")
    if len(parts) >= 3:
        return parts[-1]
    return ""


def _extract_model_from_name(name: str) -> str:
    """Extract model from mDNS name format Zendure-<Model>-<Last12MAC/SN>."""
    clean = name.replace("._zendure._tcp.local.", "").replace("._zendure._tcp.", "")
    parts = clean.split("-")
    if len(parts) >= 3:
        return parts[1]
    return "SolarFlow"
