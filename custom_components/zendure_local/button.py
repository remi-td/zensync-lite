"""Action buttons for Zendure Local Battery Control."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

try:
    from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
except ImportError:
    class ButtonEntity:  # type: ignore
        """Mock ButtonEntity."""
        pass

    @dataclass(frozen=True)
    class ButtonEntityDescription:  # type: ignore
        """Mock ButtonEntityDescription."""
        key: str
        name: str | None = None
        device_class: Any = None
        entity_category: Any = None

    class ButtonDeviceClass:  # type: ignore
        UPDATE = "update"
        RESTART = "restart"

    class EntityCategory:  # type: ignore
        DIAGNOSTIC = "diagnostic"

from .const import DOMAIN
from .coordinator import ZendureCoordinator
from .entity import ZendureEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZendureButtonEntityDescription(ButtonEntityDescription):
    """Description for Zendure button entity."""

    press_action: Callable[[ZendureCoordinator], Coroutine[Any, Any, Any]] | None = None


BUTTON_DESCRIPTIONS: tuple[ZendureButtonEntityDescription, ...] = (
    ZendureButtonEntityDescription(
        key="refresh_now",
        name="Refresh Now",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda c: c.async_request_refresh(),
    ),
    ZendureButtonEntityDescription(
        key="rediscover_endpoint",
        name="Rediscover Endpoint",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda c: c._async_try_rediscover(),
    ),
    ZendureButtonEntityDescription(
        key="test_write_path",
        name="Test Write Path",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda c: _test_write_path(c),
    ),
)


async def _test_write_path(coordinator: ZendureCoordinator) -> None:
    """Test write communication with a safe read-then-write of current confirmed limit."""
    state = coordinator.current_state
    if not state:
        _LOGGER.warning("Cannot test write path: no state available for %s", coordinator.serial)
        return

    # Use existing confirmed charge limit or target SOC to avoid changing operating parameters
    test_payload: dict[str, Any] = {}
    if state.input_limit_w is not None and coordinator.capability.can_write("inputLimit"):
        test_payload["inputLimit"] = state.input_limit_w
    elif state.target_soc_percent is not None and coordinator.capability.can_write("socSet"):
        test_payload["socSet"] = state.target_soc_percent
    else:
        _LOGGER.info("Device is read-only or no safe property found for test write")
        return

    _LOGGER.info("Testing write path on %s with payload %s", coordinator.serial, test_payload)
    success = await coordinator.async_execute_write(test_payload)
    _LOGGER.info("Test write path result for %s: %s", coordinator.serial, "Success" if success else "Failed")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zendure action buttons."""
    coordinator: ZendureCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [ZendureButton(coordinator, desc) for desc in BUTTON_DESCRIPTIONS]
    async_add_entities(entities)


class ZendureButton(ZendureEntity, ButtonEntity):
    """Representation of a Zendure button entity."""

    entity_description: ZendureButtonEntityDescription

    def __init__(
        self,
        coordinator: ZendureCoordinator,
        description: ZendureButtonEntityDescription,
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.name:
            self._attr_name = description.name

    async def async_press(self) -> None:
        """Handle button press."""
        if self.entity_description.press_action is not None:
            await self.entity_description.press_action(self.coordinator)
