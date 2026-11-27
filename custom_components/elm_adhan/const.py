"""Constants for the East London Mosque Adhan integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "elm_adhan"

# East London Mosque's Mixlr channel. The integration is deliberately scoped
# to this one broadcaster: it is the only London mosque stream found to be
# reliably live at prayer times.
CHANNEL: Final = "eastlondonmosque"
CHANNEL_PAGE: Final = f"https://{CHANNEL}.mixlr.com/"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL_MIN: Final = 5
MIN_SCAN_INTERVAL_MIN: Final = 1
MAX_SCAN_INTERVAL_MIN: Final = 60


def scan_interval(minutes: int) -> timedelta:
    """Return the coordinator interval for an options value."""
    return timedelta(minutes=minutes)
