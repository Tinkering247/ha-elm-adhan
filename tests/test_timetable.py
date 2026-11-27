"""Tests for the timetable parser and the prayer entities."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.elm_adhan.const import (
    CONF_ASR_MITHL,
    CONF_ISLAMIC_DATE_AT_MAGHRIB,
    DOMAIN,
)
from custom_components.elm_adhan.timetable import (
    LONDON,
    TimetableError,
    current_event,
    next_begins,
    next_change,
    parse_timetable,
    to_storage,
)

from .conftest import fixture_text, mock_live, mock_timetable

CURRENT = "sensor.elm_adhan_current_prayer"


def _at(*args: int) -> datetime:
    return datetime(*args, tzinfo=LONDON)


@pytest.fixture(name="timetable")
def timetable_fixture():
    """The parsed 2026 timetable."""
    return parse_timetable(fixture_text("prayer_times.html"))


# -- parser ---------------------------------------------------------------


def test_parse_whole_year(timetable) -> None:
    """Every day of 2026 parses."""
    assert len(timetable) == 365
    assert min(timetable) == date(2026, 1, 1)
    assert max(timetable) == date(2026, 12, 31)


def test_parse_day(timetable) -> None:
    """Times are resolved to 24 h London time (matches LUPT)."""
    day = timetable[date(2026, 11, 27)]
    assert day.begins("Fajr").strftime("%H:%M") == "05:53"
    assert day.begins("Zuhr").strftime("%H:%M") == "11:53"
    assert day.begins("Maghrib").strftime("%H:%M") == "16:01"
    assert day.begins("Ishā").strftime("%H:%M") == "17:37"
    assert day.begins("Asr", 1) < day.begins("Asr", 2)
    assert day.islamic_date() == "17 Jumāda Al-Ākhirah 1448"


def test_parse_summer_and_bst(timetable) -> None:
    """Late Ishā jamā‘ah stays in the evening; BST offsets apply."""
    midsummer = timetable[date(2026, 6, 21)]
    assert midsummer.jamaah("Ishā").hour == 23
    assert midsummer.begins("Fajr").hour == 2
    assert midsummer.begins("Fajr").utcoffset() == timedelta(hours=1)
    assert timetable[date(2026, 1, 1)].begins("Fajr").utcoffset() == timedelta(0)


def test_parse_midwinter_zuhr(timetable) -> None:
    """Zuhr at 11:xx is morning, 12:xx noon, 1:xx afternoon."""
    hours = {d.begins("Zuhr").hour for d in timetable.values()}
    assert hours <= {11, 12, 13}
    assert all(d.jamaah("Zuhr").hour in (12, 13) for d in timetable.values())


def test_parse_rejects_other_pages() -> None:
    """A page without the timetable raises."""
    with pytest.raises(TimetableError):
        parse_timetable("<html><table class='other'><tr><td>x</td></tr></table></html>")


def test_current_and_next(timetable) -> None:
    """Overnight it is Ishā until Fajr; the next Asr honours the mithl."""
    assert current_event(timetable, _at(2026, 11, 28, 3, 0)) == "Ishā"
    assert current_event(timetable, _at(2026, 11, 27, 16, 1)) == "Maghrib"
    assert current_event(timetable, _at(2026, 11, 27, 16, 0)) == "Asr"
    asr1 = next_begins(timetable, _at(2026, 11, 27, 12, 0), "Asr", 1)
    asr2 = next_begins(timetable, _at(2026, 11, 27, 12, 0), "Asr", 2)
    assert asr2 - asr1 > timedelta(minutes=20)
    assert next_change(timetable, _at(2026, 11, 27, 16, 0)) == _at(2026, 11, 27, 16, 1)


# -- entities -------------------------------------------------------------


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_prayer_entities(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """At 12:00 on 27 Nov it is Zuhr; next Maghrib is today at 16:01."""
    mock_live(aioclient_mock)
    await _setup(hass)

    current = hass.states.get(CURRENT)
    assert current.state == "Zuhr"
    assert current.attributes["next_prayer"] == "Asr"
    assert current.attributes["timetable_days"] == 365

    maghrib = hass.states.get("sensor.elm_adhan_maghrib")
    assert maghrib.state == "2026-11-27T16:01:00+00:00"
    assert maghrib.attributes["jamaah"] == "2026-11-27T16:08:00+00:00"
    assert hass.states.get("sensor.elm_adhan_fajr").state == "2026-11-28T05:55:00+00:00"
    assert hass.states.get("sensor.elm_adhan_isha").state == "2026-11-27T17:37:00+00:00"
    assert hass.states.get("sensor.elm_adhan_islamic_date").state == "17 Jumāda Al-Ākhirah 1448"


async def test_jamaah_disabled_by_default(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entity_registry: er.EntityRegistry
) -> None:
    """Jamā‘ah sensors exist but start disabled."""
    mock_live(aioclient_mock)
    await _setup(hass)
    reg = entity_registry.async_get("sensor.elm_adhan_maghrib_jamaah")
    assert reg is not None
    assert reg.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_asr_mithl_option(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The Asr sensor follows the chosen mithl."""
    mock_live(aioclient_mock)
    await _setup(hass, **{CONF_ASR_MITHL: "2"})
    asr = hass.states.get("sensor.elm_adhan_asr")
    assert asr.state == asr.attributes["mithl_2"].replace("+00:00", "+00:00")
    assert asr.attributes["mithl_1"] < asr.attributes["mithl_2"]


async def test_state_changes_at_prayer_time(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, frozen_time: FrozenDateTimeFactory
) -> None:
    """The current prayer flips exactly at Maghrib, with no poll needed."""
    frozen_time.move_to("2026-11-27T16:00:30+00:00")
    mock_live(aioclient_mock)
    await _setup(hass)
    assert hass.states.get(CURRENT).state == "Asr"
    assert hass.states.get("sensor.elm_adhan_islamic_date").state.startswith("17 ")

    frozen_time.move_to("2026-11-27T16:01:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(CURRENT).state == "Maghrib"
    # The Islamic day starts at Maghrib.
    assert hass.states.get("sensor.elm_adhan_islamic_date").state.startswith("18 ")
    # "Next Maghrib" rolls over to tomorrow.
    assert hass.states.get("sensor.elm_adhan_maghrib").state.startswith("2026-11-28")


async def test_islamic_date_at_midnight_option(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, frozen_time: FrozenDateTimeFactory
) -> None:
    """With the option off, the Islamic date only changes at midnight."""
    frozen_time.move_to("2026-11-27T17:00:00+00:00")
    mock_live(aioclient_mock)
    await _setup(hass, **{CONF_ISLAMIC_DATE_AT_MAGHRIB: False})
    assert hass.states.get("sensor.elm_adhan_islamic_date").state.startswith("17 ")


async def test_uses_stored_timetable_when_site_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, hass_storage, timetable
) -> None:
    """A website outage at startup falls back to the stored copy."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN)
    hass_storage[f"{DOMAIN}.timetable.{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.timetable.{entry.entry_id}",
        "data": to_storage(timetable),
    }
    aioclient_mock.clear_requests()
    mock_timetable(aioclient_mock, status=503)
    from .conftest import CHANNEL_VIEW, LIVE_URL, fixture_text as ft

    aioclient_mock.get(CHANNEL_VIEW, text=ft("channel_view_live.json"))
    aioclient_mock.get(LIVE_URL, content=b"\xff" * 2048, headers={"Content-Type": "audio/mpeg"})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(CURRENT).state == "Zuhr"


async def test_setup_retries_without_any_timetable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """No stored copy and the site down: setup is retried."""
    from .conftest import CHANNEL_VIEW, LIVE_URL, fixture_text as ft

    mock_timetable(aioclient_mock, status=503)
    aioclient_mock.get(CHANNEL_VIEW, text=ft("channel_view_live.json"))
    aioclient_mock.get(LIVE_URL, content=b"\xff" * 2048, headers={"Content-Type": "audio/mpeg"})
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_expiry_repair_issue(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    issue_registry: ir.IssueRegistry,
    frozen_time: FrozenDateTimeFactory,
) -> None:
    """Two weeks before the timetable ends, a repair issue appears."""
    frozen_time.move_to("2026-12-20T12:00:00+00:00")
    mock_live(aioclient_mock)
    await _setup(hass)
    assert issue_registry.async_get_issue(DOMAIN, "timetable_expiring") is not None


async def test_no_repair_issue_mid_year(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, issue_registry: ir.IssueRegistry
) -> None:
    """No repair issue while the timetable has plenty of days left."""
    mock_live(aioclient_mock)
    await _setup(hass)
    assert issue_registry.async_get_issue(DOMAIN, "timetable_expiring") is None
