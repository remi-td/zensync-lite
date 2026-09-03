"""Local HTTP REST transport for Zendure devices implementing ZenSDK."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any

import aiohttp

from ..const import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_CONNECT,
    DEFAULT_TIMEOUT_READ,
    TRANSPORT_LOCAL_HTTP,
)
from .base import (
    BaseTransport,
    TransportConnectionError,
    TransportError,
    TransportTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


class LocalHttpTransport(BaseTransport):
    """Primary transport communicating directly over LAN via HTTP REST."""

    def __init__(
        self,
        serial: str,
        host: str,
        port: int = 80,
        session: aiohttp.ClientSession | None = None,
        connect_timeout: float = DEFAULT_TIMEOUT_CONNECT,
        read_timeout: float = DEFAULT_TIMEOUT_READ,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialize LocalHttpTransport."""
        super().__init__(serial=serial, host=host, port=port)
        self._session = session
        self._owns_session = session is None
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._max_retries = max_retries

    @property
    def transport_type(self) -> str:
        """Return identifier."""
        return TRANSPORT_LOCAL_HTTP

    def _get_url(self, path: str) -> str:
        """Construct full URL."""
        clean_path = path.lstrip("/")
        return f"http://{self.host}:{self.port}/{clean_path}"

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure client session is active."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                connect=self._connect_timeout,
                total=self._connect_timeout + self._read_timeout,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._owns_session = True
        return self._session

    async def async_fetch_state(self) -> dict[str, Any]:
        """Fetch current state by calling GET /properties/report."""
        url = self._get_url("properties/report")
        session = await self._ensure_session()

        try:
            timeout = aiohttp.ClientTimeout(
                connect=self._connect_timeout,
                sock_read=self._read_timeout,
            )
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    text = await response.text()
                    raise TransportError(
                        f"GET {url} returned HTTP {response.status}: {text[:100]}"
                    )

                try:
                    payload = await response.json(content_type=None)
                except Exception as json_err:
                    text = await response.text()
                    raise TransportError(
                        f"Failed to parse JSON response from {url}: {json_err} - body: {text[:100]}"
                    ) from json_err

                if not isinstance(payload, dict):
                    raise TransportError(f"Unexpected JSON shape from {url}, expected dict")

                # Basic validation: check if properties dict is present
                if "properties" not in payload and "sn" not in payload:
                    raise TransportError(f"Malformed report payload missing 'properties': {payload}")

                self.last_success_time = datetime.now(timezone.utc)
                self.consecutive_failures = 0
                self.last_error = None
                return payload

        except asyncio.TimeoutError as err:
            self.consecutive_failures += 1
            self.last_error = f"Timeout connecting to {url}"
            _LOGGER.warning("Timeout fetching state from Zendure at %s", self.host)
            raise TransportTimeoutError(f"Timeout contacting {url}") from err

        except aiohttp.ClientConnectorError as err:
            self.consecutive_failures += 1
            self.last_error = f"Connection failed to {self.host}:{self.port}"
            _LOGGER.warning("Connection error contacting Zendure at %s:%s", self.host, self.port)
            raise TransportConnectionError(f"Cannot connect to {self.host}:{self.port}") from err

        except TransportError:
            self.consecutive_failures += 1
            raise

        except Exception as err:
            self.consecutive_failures += 1
            self.last_error = str(err)
            _LOGGER.exception("Unexpected error fetching state from %s: %s", url, err)
            raise TransportError(f"Unexpected HTTP error: {err}") from err

    async def async_write_properties(self, properties: dict[str, Any]) -> bool:
        """Write properties to device via POST /properties/write.
        
        Payload format:
        {
            "sn": self.serial,
            "properties": properties
        }
        """
        if not properties:
            return True

        url = self._get_url("properties/write")
        payload = {
            "sn": self.serial,
            "properties": properties,
        }
        session = await self._ensure_session()

        # Retry with exponential backoff (at most max_retries attempts)
        last_exception: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                _LOGGER.debug(
                    "Sending write attempt %d/%d to %s: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    url,
                    properties,
                )
                timeout = aiohttp.ClientTimeout(
                    connect=self._connect_timeout,
                    sock_read=self._read_timeout,
                )
                async with session.post(url, json=payload, timeout=timeout) as response:
                    if response.status in (200, 204):
                        _LOGGER.debug("Write successful to %s on attempt %d", url, attempt + 1)
                        self.last_success_time = datetime.now(timezone.utc)
                        self.consecutive_failures = 0
                        return True

                    body = await response.text()
                    _LOGGER.warning(
                        "Write rejected by %s with status %s: %s",
                        url,
                        response.status,
                        body[:200],
                    )
                    raise TransportError(f"Device responded with HTTP {response.status}: {body[:100]}")

            except (asyncio.TimeoutError, aiohttp.ClientError, TransportError) as err:
                last_exception = err
                if attempt < self._max_retries:
                    backoff = 0.5 * (2 ** attempt)
                    _LOGGER.debug("Write failed on attempt %d (%s), retrying in %.1fs", attempt + 1, err, backoff)
                    await asyncio.sleep(backoff)
                else:
                    _LOGGER.error("All %d write attempts failed for %s: %s", self._max_retries + 1, url, err)

        if isinstance(last_exception, asyncio.TimeoutError):
            raise TransportTimeoutError(f"Timeout during write to {url}") from last_exception
        if isinstance(last_exception, aiohttp.ClientConnectorError):
            raise TransportConnectionError(f"Connection failed writing to {url}") from last_exception
        if isinstance(last_exception, TransportError):
            raise last_exception

        raise TransportError(f"Failed to write properties to {url}: {last_exception}")

    async def async_check_health(self) -> bool:
        """Quick health check using GET /properties/report."""
        try:
            await self.async_fetch_state()
            return True
        except Exception:
            return False

    async def async_close(self) -> None:
        """Close HTTP session if owned."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
