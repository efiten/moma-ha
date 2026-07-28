"""Opzet voor de tests van laag 2, de Home Assistant-lijm.

Deze tests hebben Home Assistant nodig; die van `tests/protocol/` niet. Die
scheiding is geen ordening om de ordening: de snelle CI-job installeert geen
Home Assistant, dus als er ooit een HA-import in laag 1 sluipt, valt die job om.
De grens uit ontwerpbeslissing 2 wordt zo door CI afgedwongen.
"""

import json
import socket

import pytest
from homeassistant.const import CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.moma.const import CONF_SHOW_ALL_FIELDS, DOMAIN

BASE_TIMESTAMP = 1785154712978


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat Home Assistant `custom_components/` inlezen tijdens tests."""
    yield


@pytest.fixture(autouse=True)
def allow_sockets(socket_enabled):
    """Sta echte sockets toe.

    De HA-testplugin blokkeert die standaard, met goede reden: een test die het
    netwerk op gaat is traag en onbetrouwbaar. Hier is de UDP-listener juist het
    onderwerp, en alles blijft op de loopback.
    """
    yield


@pytest.fixture
def free_port() -> int:
    """Een vrije UDP-poort, zodat tests elkaar niet in de weg zitten."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def make_packet(name="TESTDEVICE01", sequence=1, timestamp=None, **fields) -> bytes:
    if timestamp is None:
        timestamp = BASE_TIMESTAMP + sequence * 5000
    return json.dumps(
        {
            "protocol": "moma",
            "version": 1,
            "type": "state",
            "name": name,
            "sequence": sequence,
            "timestamp": timestamp,
            **fields,
        }
    ).encode()


async def setup_moma(hass, port: int, *, show_all_fields: bool = False) -> MockConfigEntry:
    """Zet de integratie op met een config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Moma ({port})",
        data={CONF_PORT: port},
        options={CONF_SHOW_ALL_FIELDS: show_all_fields},
        unique_id=f"port-{port}",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def feed(hass, entry: MockConfigEntry, payload: bytes) -> None:
    """Voer één datagram aan de runtime en laat Home Assistant bijwerken.

    Rechtstreeks in plaats van via een echte socket: het aankomen van een
    datagram is niet af te wachten met `async_block_till_done`, wat de tests
    afhankelijk zou maken van timing. De socketweg zelf is apart getest.
    """
    entry.runtime_data.handle_packet(payload, "127.0.0.1:41710")
    await hass.async_block_till_done()
