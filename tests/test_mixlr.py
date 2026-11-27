"""Tests for the Mixlr resolver."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.elm_adhan.mixlr import (
    async_resolve,
    extract_stream_urls,
    iter_live_flags,
    urls_from_payload,
)

from .conftest import (
    CHANNEL_VIEW,
    LIVE_URL,
    PAGE,
    USERS,
    fixture_text,
    mock_live,
    mock_offline,
)


def test_live_flags_ignore_feature_toggles() -> None:
    """`live_streaming_enabled` is an account feature, not on-air status."""
    payload = json.loads(fixture_text("channel_view_offline.json"))
    assert payload["data"]["attributes"]["live_streaming_enabled"] is True
    assert not any(iter_live_flags(payload))


def test_extract_prefers_listen_urls() -> None:
    """Mixlr listen URLs rank ahead of archived MP3s."""
    text = '{"a":"https:\\/\\/cdn.example.org\\/old.mp3","b":"%s"}' % LIVE_URL
    assert extract_stream_urls(text)[0] == LIVE_URL


def test_broadcast_ids_become_urls() -> None:
    """/users/<channel> lists broadcast ids only."""
    payload = json.loads(fixture_text("users_live.json"))
    assert urls_from_payload(payload) == [LIVE_URL]


async def test_resolve_live(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A live channel resolves to its listen URL."""
    mock_live(aioclient_mock)
    result = await async_resolve(async_get_clientsession(hass), "eastlondonmosque")
    assert result.live
    assert result.url == LIVE_URL
    assert result.reachable


async def test_resolve_offline(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Off air there is no URL, and the channel page is not fetched."""
    mock_offline(aioclient_mock)
    result = await async_resolve(async_get_clientsession(hass), "eastlondonmosque")
    assert not result.live
    assert result.url is None
    assert result.reachable
    assert "off air" in result.source
    assert not any(str(call[1]) == PAGE for call in aioclient_mock.mock_calls)


async def test_resolve_stream_dead(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Mixlr says live but the stream is not answering."""
    aioclient_mock.get(CHANNEL_VIEW, text=fixture_text("channel_view_live.json"))
    aioclient_mock.get(LIVE_URL, status=404)
    result = await async_resolve(async_get_clientsession(hass), "eastlondonmosque")
    assert not result.live
    assert result.url == LIVE_URL
    assert "not responding" in result.source


async def test_resolve_unreachable(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Every endpoint failing marks the result unreachable."""
    for url in (CHANNEL_VIEW, USERS, PAGE):
        aioclient_mock.get(url, status=503)
    result = await async_resolve(async_get_clientsession(hass), "eastlondonmosque")
    assert not result.reachable
