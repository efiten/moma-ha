"""Tests voor opzetten, afbreken en herladen.

Het belangrijkste hier is dat de socket bij afbreken werkelijk vrijkomt. Doet hij
dat niet, dan faalt de volgende reload met `EADDRINUSE` -- en `SO_REUSEPORT`
verdoezelt dat gedeeltelijk, wat het juist verraderlijker maakt.
"""

import asyncio
import socket

from homeassistant.config_entries import ConfigEntryState

from .conftest import feed, make_packet, setup_moma


async def test_sets_up_and_listens(hass, free_port):
    entry = await setup_moma(hass, free_port)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.port == free_port


async def test_unloading_releases_the_port(hass, free_port):
    entry = await setup_moma(hass, free_port)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Zonder SO_REUSEPORT-truc opnieuw binden: lukt dat, dan is de socket echt
    # weg. Met REUSEPORT zou dit ook slagen terwijl de oude socket nog leeft.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.bind(("0.0.0.0", free_port))
    finally:
        probe.close()


async def test_can_be_reloaded(hass, free_port):
    entry = await setup_moma(hass, free_port)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


async def test_receives_a_real_datagram_over_the_socket(hass, free_port):
    # De enige test die de echte socketweg loopt. De rest voert payloads
    # rechtstreeks aan, omdat het aankomen van een datagram niet af te wachten
    # is met async_block_till_done.
    entry = await setup_moma(hass, free_port, show_all_fields=True)

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sender.sendto(make_packet(grid_power_w=2300), ("127.0.0.1", free_port))
    finally:
        sender.close()

    for _ in range(100):
        await asyncio.sleep(0.02)
        await hass.async_block_till_done()
        if hass.states.get("sensor.testdevice01_grid_power_w") is not None:
            break

    state = hass.states.get("sensor.testdevice01_grid_power_w")
    assert state is not None
    assert state.state == "2300"
    assert entry.runtime_data is not None


async def test_activation_survives_a_reload(hass, free_port):
    # Zonder persistentie zou een herstart 's nachts de PV-sensor laten
    # verdwijnen tot zonsopgang (ontwerpbeslissing 13).
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(pv_power_w=1200))
    assert hass.states.get("sensor.testdevice01_pv_power_w") is not None

    await feed(hass, entry, make_packet(sequence=2, pv_power_w=0))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    await feed(hass, entry, make_packet(sequence=3, pv_power_w=0))

    assert hass.states.get("sensor.testdevice01_pv_power_w") is not None
