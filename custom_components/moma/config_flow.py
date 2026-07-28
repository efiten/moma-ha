"""Config flow voor moma.

Er valt bijna niets te configureren: de apparaatidentiteit komt uit de broadcast,
dus geen IP-adres en geen naam. Alleen de poort, en die staat voorgevuld.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import CONF_SHOW_ALL_FIELDS, DEFAULT_PORT, DOMAIN


class MomaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Vraag de poort en maak de invoer aan."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port}
                ),
            )

        port = user_input.get(CONF_PORT, DEFAULT_PORT)

        # Twee invoeren op dezelfde poort zouden om dezelfde socket vechten.
        await self.async_set_unique_id(f"port-{port}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=f"Moma (poort {port})", data={CONF_PORT: port})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return MomaOptionsFlow()


class MomaOptionsFlow(OptionsFlow):
    """Eén optie: velden tonen die nog nooit een waarde hadden."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SHOW_ALL_FIELDS, False)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_SHOW_ALL_FIELDS, default=current): bool}
            ),
        )
