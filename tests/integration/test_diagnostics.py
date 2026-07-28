"""Tests voor diagnostics.

Doel is dat een gebruiker met afwijkende hardware één knop indrukt in plaats van
door een tcpdump-sessie gepraat te worden (ontwerpbeslissing 7). Het serienummer
mag daar niet in staan, want zulke bestanden worden in publieke issues geplakt.
"""

import json

from custom_components.moma.diagnostics import async_get_config_entry_diagnostics

from .conftest import feed, make_packet, setup_moma


async def test_includes_the_stream_summary(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(grid_power_w=2300))

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["summary"]["packets"] == 1


async def test_includes_recent_payloads(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(grid_power_w=2300))

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert len(report["recent_payloads"]) == 1


async def test_redacts_the_serial_number(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", grid_power_w=2300))

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert "Moma005000" not in json.dumps(report)


async def test_keeps_the_measurements_readable(hass, free_port):
    # Redigeren mag de bruikbaarheid niet wegnemen; de velden zijn juist waar
    # het om gaat.
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", grid_power_w=2300))

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert "grid_power_w" in json.dumps(report)


async def test_keeps_only_the_last_payloads(hass, free_port):
    # Onbegrensd bewaren zou bij een broadcast om de vijf seconden geheugen
    # blijven opeten.
    entry = await setup_moma(hass, free_port)
    for sequence in range(1, 30):
        await feed(hass, entry, make_packet(sequence=sequence, grid_power_w=sequence))

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert len(report["recent_payloads"]) <= 20
