"""Constants for the East London Mosque Adhan integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "elm_adhan"

# East London Mosque's Mixlr channel. The integration is deliberately scoped
# to this one mosque: it is the only London mosque stream found to be
# reliably live at prayer times.
CHANNEL: Final = "eastlondonmosque"
CHANNEL_PAGE: Final = f"https://{CHANNEL}.mixlr.com/"

# The mosque publishes the year's timetable (London Unified Prayer Times) here.
TIMETABLE_URL: Final = "https://www.eastlondonmosque.org.uk/prayer-times"
TIMETABLE_REFRESH: Final = timedelta(hours=12)
TIMETABLE_STORAGE_VERSION: Final = 1
# Raise a repair issue when the stored timetable runs out within this many days.
TIMETABLE_WARN_DAYS: Final = 14

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL_MIN: Final = 5
MIN_SCAN_INTERVAL_MIN: Final = 1
MAX_SCAN_INTERVAL_MIN: Final = 60

CONF_ASR_MITHL: Final = "asr_mithl"
DEFAULT_ASR_MITHL: Final = "1"
CONF_ISLAMIC_DATE_AT_MAGHRIB: Final = "islamic_date_at_maghrib"
DEFAULT_ISLAMIC_DATE_AT_MAGHRIB: Final = True


def scan_interval(minutes: int) -> timedelta:
    """Return the stream coordinator interval for an options value."""
    return timedelta(minutes=minutes)
