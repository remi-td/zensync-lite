"""Repairs handling for Zendure Local Battery Control."""

from __future__ import annotations

import logging
from typing import Any

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import issue_registry as ir
except ImportError:
    HomeAssistant = Any  # type: ignore
    ir = type("ir", (), {"IssueSeverity": type("IssueSeverity", (), {"WARNING": "warning", "ERROR": "error"}), "async_create_issue": lambda *a, **kw: None, "async_delete_issue": lambda *a, **kw: None})  # type: ignore

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_IP_UNREACHABLE = "device_ip_unreachable"
ISSUE_LOCAL_API_DISABLED = "local_api_disabled"
ISSUE_UNSUPPORTED_FIRMWARE = "unsupported_firmware"


def create_ip_unreachable_issue(hass: HomeAssistant, serial: str, host: str) -> None:
    """Create persistent issue when device IP changes and cannot be contacted."""
    try:
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_IP_UNREACHABLE}_{serial}",
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="ip_unreachable",
            translation_placeholders={"serial": serial, "host": host},
        )
    except Exception as ex:
        _LOGGER.debug("Could not create issue: %s", ex)


def clear_ip_unreachable_issue(hass: HomeAssistant, serial: str) -> None:
    """Clear issue once device connectivity is restored."""
    try:
        ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_IP_UNREACHABLE}_{serial}")
    except Exception:
        pass
