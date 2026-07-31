"""Tests voor de melding bij een apparaat dat uitsluitend nullen stuurt.

Dit is het enige geval waarin de integratie volledig correct werkt en er in de
interface tóch letterlijk niets te zien is: geen entiteiten, en zelfs geen
device. Zonder melding is dat niet te onderscheiden van een kapotte installatie,
en is de enige aanwijzing een alinea in de documentatie.
"""

from datetime import timedelta

from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.moma.const import (
    CONF_SHOW_ALL_FIELDS,
    DOMAIN,
    ISSUE_ALL_FIELDS_ZERO,
)

from .conftest import feed, make_packet, setup_moma

ALLE_VELDEN_NUL = {
    "grid_power_w": 0,
    "home_power_w": 0,
    "pv_power_w": 0,
    "battery_soc": 0,
}


def issue_id(entry) -> str:
    return f"{ISSUE_ALL_FIELDS_ZERO}_{entry.entry_id}"


async def tik(hass) -> None:
    """Laat de periodieke controle één keer lopen.

    Ruim boven het controle-interval en ruim onder de stilstandsdrempel, zodat
    deze test niet ook de beschikbaarheid omzet.
    """
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=20))
    await hass.async_block_till_done()


async def test_reports_a_device_that_only_sends_zeroes(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(**ALLE_VELDEN_NUL))
    await tik(hass)

    registry = ir.async_get(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is not None


async def test_stays_quiet_before_any_packet_arrived(hass, free_port):
    # Zonder pakketten is er niets aan de hand: dan is de juiste melding
    # "onbeschikbaar", niet "alles staat op nul".
    entry = await setup_moma(hass, free_port)
    await tik(hass)

    registry = ir.async_get(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_stays_quiet_when_a_field_has_a_value(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(**{**ALLE_VELDEN_NUL, "grid_power_w": 2300}))
    await tik(hass)

    registry = ir.async_get(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_stays_quiet_when_all_fields_are_shown(hass, free_port):
    # Met deze optie aan bestaan de entiteiten wel, dus er valt niets te melden.
    entry = await setup_moma(hass, free_port, show_all_fields=True)
    await feed(hass, entry, make_packet(**ALLE_VELDEN_NUL))
    await tik(hass)

    registry = ir.async_get(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_withdraws_the_report_after_the_advised_option_change(hass, free_port):
    # De melding raadt aan "Alle velden tonen" aan te zetten, en dat veroorzaakt
    # een reload. Zou de runtime onthouden of de melding openstaat in plaats van
    # dat op te zoeken, dan begint de nieuwe runtime op "niets open" terwijl de
    # melding er nog is -- en dan blijft die waarschuwing eeuwig staan, juist bij
    # de gebruiker die het advies opvolgde.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(**ALLE_VELDEN_NUL))
    await tik(hass)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is not None

    hass.config_entries.async_update_entry(entry, options={CONF_SHOW_ALL_FIELDS: True})
    await hass.async_block_till_done()
    await feed(hass, entry, make_packet(sequence=2, **ALLE_VELDEN_NUL))
    await tik(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_withdraws_the_report_once_a_value_arrives(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(sequence=1, **ALLE_VELDEN_NUL))
    await tik(hass)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is not None

    await feed(
        hass,
        entry,
        make_packet(sequence=2, **{**ALLE_VELDEN_NUL, "pv_power_w": 1500}),
    )
    await tik(hass)

    assert registry.async_get_issue(DOMAIN, issue_id(entry)) is None
