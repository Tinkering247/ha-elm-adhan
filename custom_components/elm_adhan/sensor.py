"""Sensors: stream URL, current prayer, prayer times and Islamic date."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_ISLAMIC_DATE_AT_MAGHRIB, DEFAULT_ISLAMIC_DATE_AT_MAGHRIB
from .coordinator import ElmAdhanConfigEntry, ElmAdhanCoordinator, TimetableCoordinator
from .entity import ElmAdhanEntity
from .timetable import (
    EVENTS,
    LONDON,
    PRAYERS,
    current_event,
    islamic_day_for,
    next_begins,
    next_event,
    next_jamaah,
)

PARALLEL_UPDATES = 0

# Event name -> translation/unique-id key.
EVENT_KEYS = {
    "Fajr": "fajr",
    "Sunrise": "sunrise",
    "Zuhr": "zuhr",
    "Asr": "asr",
    "Maghrib": "maghrib",
    "Ishā": "isha",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElmAdhanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    stream = entry.runtime_data.stream
    timetable = entry.runtime_data.timetable
    entities: list[SensorEntity] = [
        ElmAdhanStreamUrlSensor(stream, "stream_url"),
        CurrentPrayerSensor(timetable, "current_prayer"),
        IslamicDateSensor(timetable, "islamic_date"),
    ]
    entities += [PrayerTimeSensor(timetable, event) for event in EVENTS]
    entities += [JamaahSensor(timetable, prayer) for prayer in PRAYERS]
    async_add_entities(entities)


class ElmAdhanStreamUrlSensor(ElmAdhanEntity[ElmAdhanCoordinator], SensorEntity):
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


class _TimetableSensor(ElmAdhanEntity[TimetableCoordinator], SensorEntity):
    """A sensor computed from the timetable and the current time."""

    @staticmethod
    def _now() -> datetime:
        return dt_util.now(LONDON)

    @property
    def _asr_mithl(self) -> int:
        return self.coordinator.asr_mithl


class CurrentPrayerSensor(_TimetableSensor):
    """The prayer whose time has begun, e.g. `Asr` (`Ishā` overnight).

    State names match the London Unified Prayer Times integration, so it is a
    drop-in trigger for automations written against `lupt.lupt`.
    """

    # Deliberately not an ENUM sensor: enum states must be lower-case
    # translation keys, which would break compatibility with `lupt.lupt`.

    @property
    def native_value(self) -> str | None:
        """Return the current prayer."""
        return current_event(self.coordinator.data, self._now(), self._asr_mithl)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the next prayer and the timetable range."""
        upcoming = next_event(self.coordinator.data, self._now(), self._asr_mithl)
        data = self.coordinator.data
        return {
            "next_prayer": upcoming[1] if upcoming else None,
            "next_prayer_time": upcoming[0].isoformat() if upcoming else None,
            "timetable_first_day": min(data).isoformat(),
            "timetable_last_day": max(data).isoformat(),
            "timetable_days": len(data),
        }


class PrayerTimeSensor(_TimetableSensor):
    """When a prayer (or sunrise) next begins."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: TimetableCoordinator, event: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, EVENT_KEYS[event])
        self._event = event

    @property
    def native_value(self) -> datetime | None:
        """Return the next begin time."""
        return next_begins(self.coordinator.data, self._now(), self._event, self._asr_mithl)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the jamā‘ah time that follows, and both Asr times."""
        now = self._now()
        attrs: dict[str, Any] = {}
        if self._event != "Sunrise":
            jamaah = next_jamaah(self.coordinator.data, now, self._event)
            attrs["jamaah"] = jamaah.isoformat() if jamaah else None
        if self._event == "Asr":
            for mithl in (1, 2):
                when = next_begins(self.coordinator.data, now, "Asr", mithl)
                attrs[f"mithl_{mithl}"] = when.isoformat() if when else None
        return attrs or None


class JamaahSensor(_TimetableSensor):
    """When the congregation for a prayer next starts at the mosque."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: TimetableCoordinator, prayer: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, f"{EVENT_KEYS[prayer]}_jamaah")
        self._prayer = prayer

    @property
    def native_value(self) -> datetime | None:
        """Return the next jamā‘ah time."""
        return next_jamaah(self.coordinator.data, self._now(), self._prayer)


class IslamicDateSensor(_TimetableSensor):
    """Today's Islamic (Hijri) date, as published by the mosque."""

    @property
    def _day(self):
        change_at_maghrib = self.coordinator.config_entry.options.get(
            CONF_ISLAMIC_DATE_AT_MAGHRIB, DEFAULT_ISLAMIC_DATE_AT_MAGHRIB
        )
        return islamic_day_for(self.coordinator.data, self._now(), change_at_maghrib)

    @property
    def native_value(self) -> str | None:
        """Return the Islamic date."""
        day = self._day
        return day.islamic_date() if day else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the date parts."""
        day = self._day
        if not day:
            return None
        return {
            "day": day.islamic_day,
            "month": day.islamic_month,
            "year": day.islamic_year,
        }
