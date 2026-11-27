"""Fixtures for East London Mosque Adhan tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

FIXTURES = Path(__file__).parent / "fixtures"
CHANNEL_VIEW = "https://api.mixlr.com/v3/channel_view/eastlondonmosque"
USERS = "https://api.mixlr.com/users/eastlondonmosque"
PAGE = "https://eastlondonmosque.mixlr.com/"
LIVE_URL = "https://listen.mixlr.com/1150bef446b1a02469f119b82dc6264d"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/."""
    return


def fixture_text(name: str) -> str:
    """Return a recorded Mixlr payload."""
    return (FIXTURES / name).read_text()


def mock_live(aioclient_mock: AiohttpClientMocker) -> None:
    """Mixlr reports the channel live and the stream serves audio."""
    aioclient_mock.get(CHANNEL_VIEW, text=fixture_text("channel_view_live.json"))
    aioclient_mock.get(
        LIVE_URL, content=b"\xff\xfb\x90" * 700, headers={"Content-Type": "audio/mpeg"}
    )


def mock_offline(aioclient_mock: AiohttpClientMocker) -> None:
    """Mixlr reports the channel off air."""
    aioclient_mock.get(CHANNEL_VIEW, text=fixture_text("channel_view_offline.json"))
    aioclient_mock.get(USERS, text=fixture_text("users_offline.json"))
