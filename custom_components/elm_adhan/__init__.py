"""The East London Mosque Adhan integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import (
    ElmAdhanConfigEntry,
    ElmAdhanCoordinator,
    ElmAdhanData,
    TimetableCoordinator,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ElmAdhanConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    stream = ElmAdhanCoordinator(hass, entry)
    timetable = TimetableCoordinator(hass, entry)
    await stream.async_config_entry_first_refresh()
    await timetable.async_config_entry_first_refresh()

    entry.runtime_data = ElmAdhanData(stream=stream, timetable=timetable)

    timetable.async_schedule_ticks()
    entry.async_on_unload(timetable.async_cancel_ticks)
    # A refreshed timetable can move the next prayer time.
    entry.async_on_unload(timetable.async_add_listener(timetable.async_schedule_ticks))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ElmAdhanConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
