"""Stream URL sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElmAdhanConfigEntry
from .entity import ElmAdhanEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElmAdhanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor."""
    async_add_entities([ElmAdhanStreamUrlSensor(entry.runtime_data, "stream_url")])


class ElmAdhanStreamUrlSensor(ElmAdhanEntity, SensorEntity):
    """The current (or last known) live stream URL."""

    @property
    def native_value(self) -> str | None:
        """Return the stream URL."""
        return self.coordinator.data.url

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return resolver details."""
        data = self.coordinator.data
        return {
            "live": data.live,
            "source": data.source,
            "last_live": data.last_live.isoformat() if data.last_live else None,
        }
