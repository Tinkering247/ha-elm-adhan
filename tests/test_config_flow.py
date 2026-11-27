"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.elm_adhan.const import (
    CONF_ASR_MITHL,
    CONF_ISLAMIC_DATE_AT_MAGHRIB,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from .conftest import CHANNEL_VIEW, PAGE, USERS, mock_live


async def test_user_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The user confirms and an entry is created."""
    mock_live(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "East London Mosque"
    await hass.async_block_till_done()


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Mixlr being unreachable shows an error."""
    for url in (CHANNEL_VIEW, USERS, PAGE):
        aioclient_mock.get(url, status=503)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_single_instance(hass: HomeAssistant) -> None:
    """A second entry is refused."""
    MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT


async def test_options_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The polling interval can be changed."""
    mock_live(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 2, CONF_ASR_MITHL: "2", CONF_ISLAMIC_DATE_AT_MAGHRIB: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_SCAN_INTERVAL] == 2
    assert entry.runtime_data.stream.update_interval.total_seconds() == 120
    assert entry.runtime_data.timetable.asr_mithl == 2
