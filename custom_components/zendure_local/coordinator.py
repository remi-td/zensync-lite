"""DataUpdateCoordinator and Write Transaction Manager for Zendure Local Battery Control."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Callable, Generic, TypeVar

_T = TypeVar("_T")

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
except ImportError:
    # Fallback minimal implementation for standalone unit testing without full HA core
    class HomeAssistant:  # type: ignore
        """Mock HomeAssistant for testing."""
        def __init__(self) -> None:
            self.loop = asyncio.get_event_loop()

    class DataUpdateCoordinator(Generic[_T]):  # type: ignore
        """Mock DataUpdateCoordinator for testing."""
        def __init__(self, hass: Any, logger: Any, name: str, update_interval: Any) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data: Any = None
            self.last_update_success: bool = True
            self._listeners: list[Callable[[], None]] = []

        def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
            self._listeners.append(update_callback)
            return lambda: self._listeners.remove(update_callback)

        def async_update_listeners(self) -> None:
            for listener in self._listeners:
                listener()

        async def async_request_refresh(self) -> None:
            """Request a refresh."""
            try:
                self.data = await self._async_update_data()
                self.last_update_success = True
            except Exception:
                self.last_update_success = False
            self.async_update_listeners()

        async def _async_update_data(self) -> Any:
            raise NotImplementedError

    class UpdateFailed(Exception):  # type: ignore
        """Mock UpdateFailed exception."""

from .capabilities import DeviceCapability, get_device_capability
from .const import (
    CONFIRMATION_DELAY,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PROP_AC_MODE,
    PROP_INPUT_LIMIT,
    PROP_MIN_SOC,
    PROP_OUTPUT_LIMIT,
    PROP_SMART_MODE,
    PROP_SOC_SET,
    STALE_THRESHOLD_INTERVALS,
    TRANSACTION_CONFIRMED,
    TRANSACTION_FAILED,
    TRANSACTION_IDLE,
    TRANSACTION_QUEUED,
    TRANSACTION_SENT,
    TRANSACTION_TIMED_OUT,
    TRANSPORT_LOCAL_HTTP,
)
from .model import ZendureBatteryState, parse_report_payload
from .transport.base import BaseTransport, TransportError, TransportTimeoutError

_LOGGER = logging.getLogger(__name__)


class ZendureCoordinator(DataUpdateCoordinator[ZendureBatteryState]):
    """Coordinates periodic polling, write transactions, and state confirmation."""

    def __init__(
        self,
        hass: HomeAssistant,
        transport: BaseTransport,
        serial: str,
        model: str,
        poll_interval_sec: int = DEFAULT_POLL_INTERVAL,
        volatile_writes: bool = True,
        rediscover_callback: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize Zendure coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{serial}",
            update_interval=timedelta(seconds=poll_interval_sec),
        )
        self.transport = transport
        self.serial = serial
        self.model = model
        self.capability: DeviceCapability = get_device_capability(model)
        self.volatile_writes = volatile_writes
        self._rediscover_callback = rediscover_callback

        # Write lock to serialize write transactions per device
        self._write_lock = asyncio.Lock()

        # Last transaction details
        self.transaction_state: str = TRANSACTION_IDLE
        self.last_transaction_time: datetime | None = None
        self.last_transaction_detail: str | None = None
        self._last_written_payload: dict[str, Any] | None = None
        self._last_write_timestamp: float = 0.0

        # State tracking
        self.consecutive_failed_polls: int = 0
        self._cached_state: ZendureBatteryState | None = None

    @property
    def current_state(self) -> ZendureBatteryState | None:
        """Return the latest confirmed device state."""
        return self.data or self._cached_state

    async def _async_update_data(self) -> ZendureBatteryState:
        """Poll the device and parse normalized state."""
        try:
            raw_payload = await self.transport.async_fetch_state()
            self.consecutive_failed_polls = 0

            # Update capability if model is now discovered from report
            reported_model = raw_payload.get("product")
            if reported_model and reported_model != self.model:
                self.model = reported_model
                self.capability = get_device_capability(reported_model)

            state = parse_report_payload(
                payload=raw_payload,
                serial_hint=self.serial,
                model_hint=self.model,
                existing_state=self._cached_state,
                transport=self.transport.transport_type,
            )
            state.last_transaction_state = self.transaction_state
            state.last_transaction_detail = self.last_transaction_detail
            self._cached_state = state
            return state

        except Exception as err:
            self.consecutive_failed_polls += 1
            _LOGGER.warning(
                "Failed to poll Zendure %s (attempt %d/%d): %s",
                self.serial,
                self.consecutive_failed_polls,
                STALE_THRESHOLD_INTERVALS,
                err,
            )

            # Trigger automatic IP rediscovery if endpoint is unreachable
            if self.consecutive_failed_polls == 1 and self._rediscover_callback:
                _LOGGER.info("Triggering background rediscovery for %s", self.serial)
                self.hass.async_create_task(self._async_try_rediscover())

            # Mark state as stale after threshold, but PRESERVE last known telemetry
            if self._cached_state is not None:
                if self.consecutive_failed_polls >= STALE_THRESHOLD_INTERVALS:
                    self._cached_state.stale = True
                    self._cached_state.available = False
                return self._cached_state

            raise UpdateFailed(f"Error communicating with Zendure device {self.serial}: {err}") from err

    async def _async_try_rediscover(self) -> None:
        """Attempt to rediscover device address."""
        if self._rediscover_callback:
            try:
                res = self._rediscover_callback()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as ex:
                _LOGGER.debug("Rediscovery attempt failed: %s", ex)

    async def async_execute_write(
        self,
        properties: dict[str, Any],
        require_confirmation: bool = True,
    ) -> bool:
        """Execute a serialized, validated write transaction with readback confirmation.
        
        Lifecycle:
        1. Validate request against capability matrix (reject before network if invalid)
        2. Deduplicate repeated identical commands within debounce window
        3. Acquire device write lock (serialize writes)
        4. Transmit POST /properties/write
        5. Poll readback after short delay to confirm device state
        6. Update confirmed state or surface transaction failure
        """
        # Inject smartMode: 1 if volatile writes are enabled and not explicitly specified
        if self.volatile_writes and PROP_SMART_MODE not in properties:
            if self.capability.can_write(PROP_SMART_MODE):
                properties = dict(properties)
                properties[PROP_SMART_MODE] = 1

        # 1. Validation before network
        is_valid, err_msg = self.capability.validate_payload(properties)
        if not is_valid:
            self.transaction_state = TRANSACTION_FAILED
            self.last_transaction_detail = f"Validation failed: {err_msg}"
            _LOGGER.error("Rejected invalid write for %s: %s", self.serial, err_msg)
            if self._cached_state:
                self._cached_state.last_transaction_state = self.transaction_state
                self._cached_state.last_transaction_detail = self.last_transaction_detail
                self.async_update_listeners()
            return False

        # 2. Suppress identical redundant writes within 2.0s debounce window
        loop = getattr(self.hass, "loop", None)
        now_ts = loop.time() if loop else asyncio.get_event_loop().time()
        if (
            self._last_written_payload == properties
            and (now_ts - self._last_write_timestamp) < 2.0
        ):
            _LOGGER.debug("Suppressing identical redundant write for %s: %s", self.serial, properties)
            return True

        # 3. Acquire lock and begin transaction
        async with self._write_lock:
            self.transaction_state = TRANSACTION_QUEUED
            self.last_transaction_time = datetime.now(timezone.utc)
            self.last_transaction_detail = f"Queued write: {list(properties.keys())}"
            if self._cached_state:
                self._cached_state.last_transaction_state = self.transaction_state
                self._cached_state.last_transaction_detail = self.last_transaction_detail
                self.async_update_listeners()

            # 4. Transmit write
            try:
                self.transaction_state = TRANSACTION_SENT
                self.last_transaction_detail = f"Sent: {properties}"
                await self.transport.async_write_properties(properties)
                self._last_written_payload = dict(properties)
                self._last_write_timestamp = now_ts

            except TransportTimeoutError as err:
                self.transaction_state = TRANSACTION_TIMED_OUT
                self.last_transaction_detail = f"Write timed out: {err}"
                _LOGGER.error("Write timed out for %s: %s", self.serial, err)
                self._update_transaction_state_in_cache()
                return False

            except TransportError as err:
                self.transaction_state = TRANSACTION_FAILED
                self.last_transaction_detail = f"Write failed: {err}"
                _LOGGER.error("Write failed for %s: %s", self.serial, err)
                self._update_transaction_state_in_cache()
                return False

            if not require_confirmation:
                self.transaction_state = TRANSACTION_CONFIRMED
                self.last_transaction_detail = "Write sent (unconfirmed mode)"
                self._update_transaction_state_in_cache()
                return True

            # 5. Readback confirmation
            await asyncio.sleep(CONFIRMATION_DELAY)
            try:
                confirmed_state = await self._async_update_data()
                self.data = confirmed_state

                # Check if written properties match reported device truth
                confirmed = True
                mismatches = []
                for prop_name, expected_val in properties.items():
                    if prop_name == PROP_SMART_MODE:
                        continue  # smartMode may not always be reflected directly in readback properties
                    actual_val = confirmed_state.raw_properties.get(prop_name)
                    if actual_val is not None and actual_val != expected_val:
                        confirmed = False
                        mismatches.append(f"{prop_name}: expected {expected_val}, got {actual_val}")

                if confirmed:
                    self.transaction_state = TRANSACTION_CONFIRMED
                    self.last_transaction_detail = f"Confirmed {list(properties.keys())}"
                    _LOGGER.debug("Transaction confirmed for %s: %s", self.serial, properties)
                else:
                    self.transaction_state = TRANSACTION_FAILED
                    self.last_transaction_detail = f"Confirmation mismatch: {', '.join(mismatches)}"
                    _LOGGER.warning("Transaction confirmation failed for %s: %s", self.serial, self.last_transaction_detail)

                self._update_transaction_state_in_cache()
                self.async_update_listeners()
                return confirmed

            except Exception as err:
                self.transaction_state = TRANSACTION_FAILED
                self.last_transaction_detail = f"Readback check failed: {err}"
                _LOGGER.warning("Failed during readback confirmation for %s: %s", self.serial, err)
                self._update_transaction_state_in_cache()
                return False

    def _update_transaction_state_in_cache(self) -> None:
        """Sync transaction state to cached state."""
        if self._cached_state:
            self._cached_state.last_transaction_state = self.transaction_state
            self._cached_state.last_transaction_detail = self.last_transaction_detail
            self.async_update_listeners()

    def update_endpoint(self, host: str, port: int | None = None) -> None:
        """Update transport IP and reconnect."""
        self.transport.update_endpoint(host, port)
        self.consecutive_failed_polls = 0
        _LOGGER.info("Updated endpoint for %s to %s:%s", self.serial, host, port or self.transport.port)

    async def async_close(self) -> None:
        """Shut down coordinator and transport."""
        await self.transport.async_close()
