"""Coordinators for the East London Mosque stream and timetable."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CHANNEL,
    CONF_ASR_MITHL,
    CONF_SCAN_INTERVAL,
    DEFAULT_ASR_MITHL,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    TIMETABLE_REFRESH,
    TIMETABLE_STORAGE_VERSION,
    TIMETABLE_URL,
    TIMETABLE_WARN_DAYS,
    scan_interval,
)
from .mixlr import USER_AGENT, async_resolve
from .timetable import (
    LONDON,
    Timetable,
    TimetableError,
    from_storage,
    next_change,
    parse_timetable,
    to_storage,
)

_LOGGER = logging.getLogger(__name__)

ISSUE_TIMETABLE_EXPIRING = "timetable_expiring"


@dataclass
class ElmAdhanData:
    """Runtime data for a config entry."""

    stream: ElmAdhanCoordinator
    timetable: TimetableCoordinator


type ElmAdhanConfigEntry = ConfigEntry[ElmAdhanData]


@dataclass
class StreamState:
    """What the stream entities expose."""

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
            name=f"{DOMAIN} stream",
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


class TimetableCoordinator(DataUpdateCoordinator[Timetable]):
    """Fetch the mosque's yearly timetable, and tick entities at each prayer.

    The last good timetable is kept in storage, so a website outage or a
    restart never leaves the prayer entities without data.
    """

    config_entry: ElmAdhanConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ElmAdhanConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} timetable",
            update_interval=TIMETABLE_REFRESH,
        )
        self._session = async_get_clientsession(hass)
        self._store: Store[dict] = Store(
            hass, TIMETABLE_STORAGE_VERSION, f"{DOMAIN}.timetable.{entry.entry_id}"
        )
        self._stored: Timetable | None = None
        self._unsub_tick: Callable[[], None] | None = None
        self.last_fetch_error: str | None = None

    @property
    def asr_mithl(self) -> int:
        """Return which Asr time (1st or 2nd mithl) counts as Asr beginning."""
        return int(self.config_entry.options.get(CONF_ASR_MITHL, DEFAULT_ASR_MITHL))

    async def _async_setup(self) -> None:
        """Load the stored timetable."""
        if raw := await self._store.async_load():
            try:
                self._stored = from_storage(raw)
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.warning("Ignoring unreadable stored timetable: %s", err)

    async def _async_update_data(self) -> Timetable:
        """Fetch and parse the timetable, falling back to the stored copy."""
        try:
            async with self._session.get(
                TIMETABLE_URL,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                resp.raise_for_status()
                page = await resp.text()
            timetable = await self.hass.async_add_executor_job(parse_timetable, page)
        except (aiohttp.ClientError, TimeoutError, TimetableError) as err:
            self.last_fetch_error = str(err)
            fallback = self.data or self._stored
            if fallback:
                _LOGGER.warning("Could not refresh the timetable, using the stored copy: %s", err)
                self._check_expiry(fallback)
                return fallback
            raise UpdateFailed(f"Could not fetch the prayer timetable: {err}") from err

        self.last_fetch_error = None
        # Keep days we already had that the page no longer lists (e.g. last
        # year's December once the page switches to the new year).
        merged = {**(self.data or self._stored or {}), **timetable}
        await self._store.async_save(to_storage(merged))
        self._stored = merged
        self._check_expiry(merged)
        return merged

    def _check_expiry(self, timetable: Timetable) -> None:
        """Raise a repair issue when the timetable is about to run out."""
        last_day = max(timetable)
        today = dt_util.now(LONDON).date()
        if last_day - today <= timedelta(days=TIMETABLE_WARN_DAYS):
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_TIMETABLE_EXPIRING,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_TIMETABLE_EXPIRING,
                translation_placeholders={
                    "last_day": last_day.isoformat(),
                    "url": TIMETABLE_URL,
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_TIMETABLE_EXPIRING)

    @callback
    def async_schedule_ticks(self) -> None:
        """Update listeners at the next prayer time, then keep rescheduling."""
        self.async_cancel_ticks()
        if not self.data:
            return
        when = next_change(self.data, dt_util.now(LONDON), self.asr_mithl)
        if when is None:
            return
        self._unsub_tick = async_track_point_in_utc_time(
            self.hass, self._async_tick, dt_util.as_utc(when)
        )

    @callback
    def _async_tick(self, _now: datetime) -> None:
        self._unsub_tick = None
        self.async_update_listeners()
        self.async_schedule_ticks()

    @callback
    def async_cancel_ticks(self) -> None:
        """Stop the prayer-time ticks."""
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
