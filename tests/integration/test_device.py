"""Tests voor het device, los van de vraag of er sensoren zijn.

Een apparaat waarvan elk veld op nul staat activeert geen enkel veld. Zou het
device alleen via `DeviceInfo` van de sensoren ontstaan, dan blijft de
integratiepagina in dat geval helemaal leeg -- van buiten niet te onderscheiden
van een broadcast die nooit aankwam.
"""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.moma import async_remove_config_entry_device
from custom_components.moma.const import DOMAIN
from custom_components.moma.device import device_details

from .conftest import feed, make_packet, setup_moma

ALLE_VELDEN_NUL = {"grid_power_w": 0, "home_power_w": 0, "battery_soc": 0}


async def test_creates_the_device_even_without_sensors(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", **ALLE_VELDEN_NUL))

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})

    assert device is not None


async def test_that_device_really_has_no_entities(hass, free_port):
    # De melding is "gevonden, niets te meten". Zouden er tóch entiteiten
    # ontstaan, dan is beslissing 13 stuk en zegt deze test dat.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", **ALLE_VELDEN_NUL))

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})
    entiteiten = er.async_entries_for_device(er.async_get(hass), device.id)

    assert entiteiten == []


async def test_describes_the_device_without_sensors(hass, free_port):
    # Zonder deze velden staat er een naamloos kaartje, en dan schiet het
    # aanmaken van het device zijn doel voorbij.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", **ALLE_VELDEN_NUL))

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})

    assert (device.manufacturer, device.model, device.serial_number) == (
        "Moma",
        "Moma",
        "005000",
    )


async def test_does_not_duplicate_the_device_once_sensors_appear(hass, free_port):
    # Twee paden maken dit device aan: de runtime bij het eerste pakket, en het
    # DeviceInfo van elke sensor. Lopen de identifiers uiteen, dan staan er
    # ineens twee kaarten voor hetzelfde apparaat.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(sequence=1, name="Moma005000", **ALLE_VELDEN_NUL))
    await feed(
        hass,
        entry,
        make_packet(sequence=2, name="Moma005000", **{**ALLE_VELDEN_NUL, "grid_power_w": 2300}),
    )

    registry = dr.async_get(hass)
    moma_devices = [
        device
        for device in registry.devices.values()
        if any(domein == DOMAIN for domein, _ in device.identifiers)
    ]

    assert len(moma_devices) == 1


async def test_survives_a_reload(hass, free_port):
    # Het device hangt aan de config entry. Een reload mag het niet opruimen,
    # want dan knippert het kaartje weg bij elke optiewijziging.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", **ALLE_VELDEN_NUL))

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})

    assert device is not None


async def test_refuses_to_remove_a_device_that_still_broadcasts(hass, free_port):
    # Toestaan zou een knop opleveren die niets doet: het apparaat staat binnen
    # vijf seconden weer in het register.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", grid_power_w=2300))
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})

    assert await async_remove_config_entry_device(hass, entry, device) is False


async def test_allows_removing_a_device_that_no_longer_broadcasts(hass, free_port):
    # Zoals een vervangen apparaat met een oud serienummer: het staat nog in het
    # register uit een eerdere sessie, maar stuurt niets meer.
    entry = await setup_moma(hass, free_port)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **device_details("Moma005000")
    )

    assert await async_remove_config_entry_device(hass, entry, device) is True


async def test_removing_a_device_forgets_its_activated_fields(hass, free_port):
    # Na een herstart is de tracker leeg maar staat de activeringsstatus nog in
    # de opslag. Bleef die na verwijderen staan, dan komen de sensoren bij een
    # terugkomst meteen terug in plaats van pas na een echte meting.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", grid_power_w=2300))
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "Moma005000")})
    assert entry.runtime_data.tracker.activation_state() != {}

    await async_remove_config_entry_device(hass, entry, device)

    assert entry.runtime_data.tracker.activation_state() == {}
