"""On-air binary sensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up the binary sensor."""
    async_add_entities([ElmAdhanLiveBinarySensor(entry.runtime_data, "live")])


class ElmAdhanLiveBinarySensor(ElmAdhanEntity, BinarySensorEntity):
    """On while East London Mosque is broadcasting and the stream answers."""

    @property
    def is_on(self) -> bool:
        """Return whether the stream is live."""
        return self.coordinator.data.live
