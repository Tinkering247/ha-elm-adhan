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
    coordinator = entry.runtime_data
    data = asdict(coordinator.data) if coordinator.data else None
    if data and data["last_live"]:
        data["last_live"] = data["last_live"].isoformat()
    return {
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "data": data,
    }
