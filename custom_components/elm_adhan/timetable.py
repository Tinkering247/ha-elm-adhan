"""Parse East London Mosque's published prayer timetable.

The mosque's prayer-times page embeds the whole year as a plain HTML table
(class `tableizer-table`): one row per day with the Gregorian and Islamic
date, and begin and jamā‘ah times written as 12-hour `h:mm` without am/pm.

This module has no Home Assistant imports so it can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
import re
import unicodedata
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
TABLE_CLASS = "tableizer-table"

# The five daily prayers plus sunrise, in the order they occur. State names
# match the London Unified Prayer Times integration (`lupt`), so automations
# written for it keep working.
FAJR, SUNRISE, ZUHR, ASR, MAGHRIB, ISHA = "Fajr", "Sunrise", "Zuhr", "Asr", "Maghrib", "Ishā"
EVENTS = (FAJR, SUNRISE, ZUHR, ASR, MAGHRIB, ISHA)
PRAYERS = (FAJR, ZUHR, ASR, MAGHRIB, ISHA)

# Normalised column heading -> internal key.
_COLUMNS = {
    "gregorian date": "date",
    "islamic day": "islamic_day",
    "islamic month": "islamic_month",
    "islamic year": "islamic_year",
    "sunrise": "sunrise",
    "fajr begins": "fajr",
    "fajr jamaah": "fajr_jamaah",
    "zuhr begins": "zuhr",
    "zuhr jamaah": "zuhr_jamaah",
    "asr mithl 1": "asr_mithl_1",
    "asr mithl 2": "asr_mithl_2",
    "asr jamaah": "asr_jamaah",
    "maghrib begins": "maghrib",
    "maghrib jamaah": "maghrib_jamaah",
    "isha begins": "isha",
    "isha jamaah": "isha_jamaah",
}
TIME_KEYS = tuple(k for k in _COLUMNS.values() if k not in {"date", "islamic_day", "islamic_month", "islamic_year"})

_TIME_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


class TimetableError(Exception):
    """The page did not contain a usable timetable."""


@dataclass(frozen=True)
class Day:
    """One day of the timetable. Times are timezone-aware (Europe/London)."""

    day: date
    islamic_day: int | None
    islamic_month: str
    islamic_year: int | None
    times: dict[str, datetime]

    def begins(self, event: str, asr_mithl: int = 1) -> datetime:
        """Return when an event (Fajr, Sunrise, Zuhr, Asr, Maghrib, Ishā) begins."""
        if event == ASR:
            return self.times[f"asr_mithl_{asr_mithl}"]
        return self.times[_key(event)]

    def jamaah(self, prayer: str) -> datetime | None:
        """Return the congregation time for a prayer."""
        return self.times.get(f"{_key(prayer)}_jamaah")

    def islamic_date(self) -> str:
        """Return the Islamic date, e.g. `17 Jumāda Al-Ākhirah 1448`."""
        return " ".join(str(p) for p in (self.islamic_day, self.islamic_month, self.islamic_year) if p)


Timetable = dict[date, Day]


def _key(event: str) -> str:
    return {FAJR: "fajr", SUNRISE: "sunrise", ZUHR: "zuhr", ASR: "asr", MAGHRIB: "maghrib", ISHA: "isha"}[event]


def _normalise(text: str) -> str:
    """Lower-case, strip accents and punctuation: `Ishā Jamā'ah` -> `isha jamaah`."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 ]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _to_24h(key: str, hour: int) -> int:
    """Resolve a 12-hour clock reading using what each column can contain."""
    if key.startswith(("fajr", "sunrise")):
        return hour % 12
    if key.startswith("zuhr"):
        # 11:xx is late morning in midwinter; 12:xx is noon; 1:xx is pm.
        return hour if hour >= 11 else hour + 12
    # Asr, Maghrib and Ishā are always afternoon or evening.
    return hour % 12 + 12


class _TableParser(HTMLParser):
    """Collect the header and cell text of the first `tableizer-table`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._depth = 0  # >0 while inside the target table
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        if tag == "table":
            classes = (dict(attrs).get("class") or "").split()
            if self._depth or TABLE_CLASS in classes:
                self._depth += 1
            return
        if not self._depth:
            return
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self._depth or self._done:
            return
        if tag == "table":
            self._depth -= 1
            if not self._depth:
                self._done = True
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if not self.headers:
                self.headers = self._row
            elif any(self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_timetable(page: str) -> Timetable:
    """Parse the prayer-times page into a timetable keyed by date."""
    parser = _TableParser()
    parser.feed(page)
    if not parser.headers or not parser.rows:
        raise TimetableError("prayer timetable table not found")

    columns = {i: _COLUMNS[n] for i, h in enumerate(parser.headers) if (n := _normalise(h)) in _COLUMNS}
    missing = set(_COLUMNS.values()) - set(columns.values())
    if missing:
        raise TimetableError(f"timetable is missing columns: {', '.join(sorted(missing))}")

    timetable: Timetable = {}
    for row in parser.rows:
        cells = {key: row[i] for i, key in columns.items() if i < len(row)}
        try:
            day = datetime.strptime(cells["date"], "%d/%m/%Y").date()
        except (KeyError, ValueError):
            continue
        times: dict[str, datetime] = {}
        for key in TIME_KEYS:
            match = _TIME_RE.match(cells.get(key, ""))
            if not match:
                continue
            hour, minute = int(match[1]), int(match[2])
            if not (1 <= hour <= 12 and minute < 60):
                continue
            times[key] = datetime.combine(day, time(_to_24h(key, hour), minute), LONDON)
        if not all(k in times for k in ("fajr", "sunrise", "zuhr", "asr_mithl_1", "asr_mithl_2", "maghrib", "isha")):
            continue
        timetable[day] = Day(
            day=day,
            islamic_day=_int(cells.get("islamic_day")),
            islamic_month=cells.get("islamic_month", ""),
            islamic_year=_int(cells.get("islamic_year")),
            times=times,
        )

    if not timetable:
        raise TimetableError("timetable has no usable rows")
    return timetable


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def to_storage(timetable: Timetable) -> dict[str, dict]:
    """Serialise a timetable for Home Assistant's Store."""
    return {
        d.isoformat(): {
            "islamic_day": day.islamic_day,
            "islamic_month": day.islamic_month,
            "islamic_year": day.islamic_year,
            "times": {k: v.isoformat() for k, v in day.times.items()},
        }
        for d, day in timetable.items()
    }


def from_storage(data: dict[str, dict]) -> Timetable:
    """Rebuild a timetable stored with `to_storage`."""
    timetable: Timetable = {}
    for d, raw in data.items():
        day = date.fromisoformat(d)
        timetable[day] = Day(
            day=day,
            islamic_day=raw.get("islamic_day"),
            islamic_month=raw.get("islamic_month", ""),
            islamic_year=raw.get("islamic_year"),
            times={k: datetime.fromisoformat(v) for k, v in raw["times"].items()},
        )
    return timetable


# --------------------------------------------------------------------------
# Queries
# --------------------------------------------------------------------------


def _events_around(timetable: Timetable, now: datetime, asr_mithl: int) -> list[tuple[datetime, str]]:
    """Begin times from yesterday to tomorrow, sorted."""
    today = now.astimezone(LONDON).date()
    events: list[tuple[datetime, str]] = []
    for offset in (-1, 0, 1, 2):
        day = timetable.get(today + timedelta(days=offset))
        if day:
            events.extend((day.begins(e, asr_mithl), e) for e in EVENTS)
    return sorted(events)


def current_event(timetable: Timetable, now: datetime, asr_mithl: int = 1) -> str | None:
    """Return the most recent event that has begun (`Ishā` overnight until Fajr)."""
    past = [e for e in _events_around(timetable, now, asr_mithl) if e[0] <= now]
    return past[-1][1] if past else None


def next_event(
    timetable: Timetable, now: datetime, asr_mithl: int = 1
) -> tuple[datetime, str] | None:
    """Return the next event to begin."""
    future = [e for e in _events_around(timetable, now, asr_mithl) if e[0] > now]
    return future[0] if future else None


def next_begins(
    timetable: Timetable, now: datetime, event: str, asr_mithl: int = 1
) -> datetime | None:
    """Return the next time an event begins, today or tomorrow."""
    today = now.astimezone(LONDON).date()
    for offset in (0, 1):
        day = timetable.get(today + timedelta(days=offset))
        if day and (when := day.begins(event, asr_mithl)) > now:
            return when
    return None


def next_jamaah(timetable: Timetable, now: datetime, prayer: str) -> datetime | None:
    """Return the next congregation time for a prayer, today or tomorrow."""
    today = now.astimezone(LONDON).date()
    for offset in (0, 1):
        day = timetable.get(today + timedelta(days=offset))
        if day and (when := day.jamaah(prayer)) and when > now:
            return when
    return None


def islamic_day_for(
    timetable: Timetable, now: datetime, change_at_maghrib: bool
) -> Day | None:
    """Return the timetable row whose Islamic date applies now.

    The Islamic day begins at sunset, so with `change_at_maghrib` the next
    row's Islamic date is used from Maghrib onwards.
    """
    today = now.astimezone(LONDON).date()
    day = timetable.get(today)
    if day and change_at_maghrib and now >= day.begins(MAGHRIB):
        return timetable.get(today + timedelta(days=1)) or day
    return day


def next_change(
    timetable: Timetable, now: datetime, asr_mithl: int = 1
) -> datetime | None:
    """Return the next moment any entity's value changes.

    That is the next begin or jamā‘ah time, or midnight (when "next" times
    roll over to tomorrow).
    """
    today = now.astimezone(LONDON).date()
    candidates: list[datetime] = [
        datetime.combine(today + timedelta(days=1), time(0, 0), LONDON)
    ]
    for offset in (0, 1):
        day = timetable.get(today + timedelta(days=offset))
        if day:
            candidates.extend(day.times.values())
    future = [c for c in candidates if c > now]
    return min(future) if future else None
