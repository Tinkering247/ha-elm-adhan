"""Polling coordinator for the East London Mosque stream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CHANNEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    scan_interval,
)
from .mixlr import async_resolve

_LOGGER = logging.getLogger(__name__)

type ElmAdhanConfigEntry = ConfigEntry[ElmAdhanCoordinator]


@dataclass
class StreamState:
    """What the entities expose."""

    url: str | None
    live: bool
    source: str
    last_live: datetime | None


class ElmAdhanCoordinator(DataUpdateCoordinator[StreamState]):
    """Poll Mixlr for East London Mosque's live stream."""

    config_entry: ElmAdhanConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ElmAdhanConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=scan_interval(
                entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN)
            ),
        )
        self._session = async_get_clientsession(hass)
        self._last_url: str | None = None
        self._last_live: datetime | None = None

    async def _async_update_data(self) -> StreamState:
        """Resolve the stream."""
        result = await async_resolve(self._session, CHANNEL)
        if not result.reachable:
            raise UpdateFailed("Mixlr could not be reached")

        if result.live and result.url:
            self._last_url = result.url
            self._last_live = dt_util.utcnow()

        return StreamState(
            # Off air, keep the last URL that played, for reference.
            url=result.url if result.live else self._last_url,
            live=result.live,
            source=result.source,
            last_live=self._last_live,
        )
