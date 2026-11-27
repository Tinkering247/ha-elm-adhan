"""Diagnostics for the East London Mosque Adhan integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import ElmAdhanConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ElmAdhanConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    stream = entry.runtime_data.stream
    timetable = entry.runtime_data.timetable

    stream_data = asdict(stream.data) if stream.data else None
    if stream_data and stream_data["last_live"]:
        stream_data["last_live"] = stream_data["last_live"].isoformat()

    days = timetable.data or {}
    return {
        "options": dict(entry.options),
        "stream": {
            "last_update_success": stream.last_update_success,
            "data": stream_data,
        },
        "timetable": {
            "last_update_success": timetable.last_update_success,
            "last_fetch_error": timetable.last_fetch_error,
            "days": len(days),
            "first_day": min(days).isoformat() if days else None,
            "last_day": max(days).isoformat() if days else None,
        },
    }
