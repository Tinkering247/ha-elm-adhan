"""Config flow for the East London Mosque Adhan integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CHANNEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MAX_SCAN_INTERVAL_MIN,
    MIN_SCAN_INTERVAL_MIN,
)
from .mixlr import async_resolve

TITLE = "East London Mosque"


class ElmAdhanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance config flow: there is only one East London Mosque."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup after checking Mixlr is reachable."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            result = await async_resolve(
                async_get_clientsession(self.hass), CHANNEL, probe=False
            )
            if result.reachable:
                return self.async_create_entry(title=TITLE, data={})
            errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ElmAdhanOptionsFlow:
        """Return the options flow."""
        return ElmAdhanOptionsFlow()


class ElmAdhanOptionsFlow(OptionsFlowWithReload):
    """Let the user change how often Mixlr is polled."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN
                    ),
                ): vol.All(
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_MIN,
                            max=MAX_SCAN_INTERVAL_MIN,
                            step=1,
                            unit_of_measurement="min",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Coerce(int),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
