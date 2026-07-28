"""Tests voor de config flow.

De integratie is bewust configuratieloos: de identiteit komt uit de broadcast,
dus er is geen IP-adres of naam nodig. Alleen de poort, en die staat voorgevuld.
"""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PORT
from homeassistant.data_entry_flow import FlowResultType

from custom_components.moma.const import CONF_SHOW_ALL_FIELDS, DEFAULT_PORT, DOMAIN


async def test_the_form_offers_the_default_port(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_creates_an_entry_with_the_default_port(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == DEFAULT_PORT


async def test_accepts_a_different_port(hass, free_port):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: free_port}
    )
    await hass.async_block_till_done()

    assert result["data"][CONF_PORT] == free_port


async def test_refuses_a_second_entry_on_the_same_port(hass, free_port):
    # Twee entries op dezelfde poort zouden om dezelfde socket vechten.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: free_port})
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: free_port}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_show_all_fields_is_off_by_default(hass, free_port):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: free_port}
    )
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(result["result"].entry_id)

    assert entry.options.get(CONF_SHOW_ALL_FIELDS, False) is False


async def test_options_flow_can_switch_on_showing_all_fields(hass, free_port):
    # De knop die je bij een testinstallatie nodig hebt: zonder deze optie
    # krijg je bij een inactief apparaat een device zonder sensoren.
    from .conftest import setup_moma

    entry = await setup_moma(hass, free_port)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SHOW_ALL_FIELDS: True}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SHOW_ALL_FIELDS] is True
