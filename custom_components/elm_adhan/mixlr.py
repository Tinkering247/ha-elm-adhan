"""Resolve a Mixlr channel's live stream URL without a browser.

Mixlr's public page is JavaScript-heavy, but the same data is served by its
JSON API. The resolver tries the API first, falls back to the inline JSON
embedded in the channel page, then probes the URL to confirm audio is
actually flowing.

This module has no Home Assistant imports so it can be tested in isolation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

USER_AGENT = "ha-elm-adhan (+https://github.com/Tinkering247/ha-elm-adhan)"
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=12)

API_ENDPOINTS = (
    "https://api.mixlr.com/v3/channel_view/{channel}",
    "https://api.mixlr.com/users/{channel}",
)

# Mixlr hands out opaque listen URLs; anything else must look like audio.
MIXLR_LISTEN_RE = re.compile(r"https?://listen\.mixlr\.com/[0-9a-zA-Z._-]{8,}")
AUDIO_URL_RE = re.compile(
    r"""https?://[^\s"'<>\\)]+?\.(?:m3u8|mp3|aac|ogg|opus)(?:\?[^\s"'<>\\)]*)?""",
    re.IGNORECASE,
)
JUNK_URL_HINTS = ("notification", "placeholder", "example.", "sample", "sprite", "silence")

# Only these keys report on-air status. Keys such as `live_streaming_enabled`
# or `live_embed_player_enabled` are account features, true even off air.
LIVE_KEYS = frozenset({"live", "is_live"})


@dataclass
class Resolution:
    """The outcome of one resolve pass."""

    url: str | None = None
    live: bool = False
    reachable: bool = False
    source: str = "not resolved"
    candidates: list[str] = field(default_factory=list)


def iter_strings(obj: Any) -> Iterator[str]:
    """Yield every string in a nested JSON structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from iter_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from iter_strings(value)


def iter_live_flags(obj: Any) -> Iterator[bool]:
    """Yield every boolean stored under an on-air status key."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, bool) and key.lower() in LIVE_KEYS:
                yield value
            else:
                yield from iter_live_flags(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from iter_live_flags(value)


def extract_stream_urls(text: str) -> list[str]:
    """Pull plausible stream URLs out of HTML or JSON, best guess first."""
    # Inline JSON in HTML escapes its slashes; unescape so URLs match whole.
    text = text.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    found: list[str] = []
    for match in MIXLR_LISTEN_RE.findall(text) + AUDIO_URL_RE.findall(text):
        url = match.rstrip("\\\"'")
        if any(hint in url.lower() for hint in JUNK_URL_HINTS):
            continue
        if url not in found:
            found.append(url)

    def rank(pair: tuple[int, str]) -> tuple[bool, bool, int]:
        position, url = pair
        is_listen = "listen.mixlr.com" in url
        # A bare .mp3 off-platform is usually an archived recording.
        archived = url.lower().endswith(".mp3") and not is_listen
        return (archived, not is_listen, position)

    return [url for _, url in sorted(enumerate(found), key=rank)]


def urls_from_payload(payload: Any) -> list[str]:
    """Find stream URLs in an API payload, including bare broadcast ids."""
    urls = extract_stream_urls(json.dumps(payload))
    if not urls and isinstance(payload, dict):
        # /users/<channel> lists broadcast ids rather than URLs.
        for broadcast_id in payload.get("broadcast_ids") or []:
            if isinstance(broadcast_id, str) and re.fullmatch(r"[0-9a-f]{16,}", broadcast_id):
                urls.append(f"https://listen.mixlr.com/{broadcast_id}")
    return urls


async def _get(session: aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse | None:
    """GET a URL and read its body, or return None on any failure."""
    try:
        async with session.get(
            url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}
        ) as resp:
            if resp.status >= 400:
                _LOGGER.debug("GET %s -> HTTP %s", url, resp.status)
                return None
            await resp.read()
            return resp
    except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as err:
        _LOGGER.debug("GET %s failed: %s", url, err)
        return None


async def probe_stream(session: aiohttp.ClientSession, url: str) -> bool:
    """Return True if the URL is serving audio right now."""
    try:
        # No Range header: Icecast mounts often answer 416 to one. Read a
        # couple of KB off the front and hang up instead.
        async with session.get(
            url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}
        ) as resp:
            if resp.status >= 400:
                _LOGGER.debug("probe %s -> HTTP %s", url, resp.status)
                return False
            content_type = resp.headers.get("Content-Type", "").lower()
            body = await resp.content.read(2048)
            if not body:
                return False
            if any(kind in content_type for kind in ("audio", "mpegurl", "octet-stream", "video")):
                return True
            # Some mounts mislabel their type; an HLS playlist is text.
            return body.lstrip().startswith(b"#EXTM3U")
    except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as err:
        _LOGGER.debug("probe %s failed: %s", url, err)
        return False


async def async_resolve(
    session: aiohttp.ClientSession, channel: str, *, probe: bool = True
) -> Resolution:
    """Resolve the channel's current stream URL and whether it is live."""
    result = Resolution()
    explicitly_live: bool | None = None

    for template in API_ENDPOINTS:
        resp = await _get(session, template.format(channel=channel))
        if resp is None:
            continue
        result.reachable = True
        try:
            payload = await resp.json(content_type=None)
        except (ValueError, aiohttp.ContentTypeError):
            continue
        flags = list(iter_live_flags(payload))
        if flags:
            explicitly_live = any(flags)
        result.candidates = urls_from_payload(payload)
        if result.candidates or explicitly_live is False:
            result.source = template.split("/{")[0].removeprefix("https://")
            break

    if not result.candidates and explicitly_live is not False:
        resp = await _get(session, f"https://{channel}.mixlr.com/")
        if resp is not None:
            result.reachable = True
            result.candidates = extract_stream_urls(await resp.text())
            if result.candidates:
                result.source = "channel page"

    if explicitly_live is False:
        result.source = f"{result.source}: off air"
        return result

    if not result.candidates:
        result.source = "no stream URL found"
        return result

    if not probe:
        result.url = result.candidates[0]
        result.live = bool(explicitly_live)
        return result

    for candidate in result.candidates[:3]:
        if await probe_stream(session, candidate):
            result.url = candidate
            result.live = True
            return result

    result.url = result.candidates[0]
    result.source = f"{result.source}: stream not responding"
    return result
