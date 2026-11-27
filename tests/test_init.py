"""Tests for setup and entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.elm_adhan.const import DOMAIN

from .conftest import CHANNEL_VIEW, LIVE_URL, PAGE, USERS, mock_live, mock_offline, mock_timetable

SENSOR = "sensor.elm_adhan_stream_url"
BINARY = "binary_sensor.elm_adhan_live"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_live(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Live: the sensor has the URL and the binary sensor is on."""
    mock_live(aioclient_mock)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(SENSOR).state == LIVE_URL
    assert hass.states.get(SENSOR).attributes["live"] is True
    assert hass.states.get(BINARY).state == STATE_ON


async def test_goes_off_air_keeps_last_url(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Off air after being live: binary off, URL kept for reference."""
    mock_live(aioclient_mock)
    entry = await _setup(hass)

    aioclient_mock.clear_requests()
    mock_offline(aioclient_mock)
    await entry.runtime_data.stream.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(BINARY).state == STATE_OFF
    assert hass.states.get(SENSOR).state == LIVE_URL
    assert hass.states.get(SENSOR).attributes["last_live"] is not None


async def test_unreachable_marks_unavailable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Mixlr unreachable after setup makes the entities unavailable."""
    mock_live(aioclient_mock)
    entry = await _setup(hass)

    aioclient_mock.clear_requests()
    for url in (CHANNEL_VIEW, USERS, PAGE):
        aioclient_mock.get(url, status=503)
    await entry.runtime_data.stream.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(BINARY).state == STATE_UNAVAILABLE


async def test_setup_retries_when_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Setup is retried if Mixlr cannot be reached at startup."""
    for url in (CHANNEL_VIEW, USERS, PAGE):
        aioclient_mock.get(url, status=503)
    mock_timetable(aioclient_mock)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The entry unloads cleanly."""
    mock_live(aioclient_mock)
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
