"""Tests voor de UDP-listener.

Deze tests binden op 127.0.0.1 in plaats van 0.0.0.0 om geen
firewall-dialoog uit te lokken tijdens het ontwikkelen op Windows.
"""

import asyncio
import socket

import pytest

from protocol.listener import open_listener


async def send_to(port, payload, *, host="127.0.0.1"):
    """Verstuur één datagram naar de listener."""
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sender.sendto(payload, (host, port))
    finally:
        sender.close()


async def test_delivers_a_received_datagram_to_the_callback():
    received: asyncio.Queue = asyncio.Queue()

    listener = await open_listener(
        port=0, bind="127.0.0.1", on_packet=lambda payload, source: received.put_nowait((payload, source))
    )
    try:
        await send_to(listener.port, b"hallo")
        payload, source = await asyncio.wait_for(received.get(), timeout=2)
    finally:
        listener.close()

    assert payload == b"hallo"
    assert source.startswith("127.0.0.1:")


async def test_reports_the_port_it_actually_bound():
    listener = await open_listener(port=0, bind="127.0.0.1", on_packet=lambda payload, source: None)
    try:
        assert listener.port > 0
    finally:
        listener.close()


async def test_a_failing_callback_does_not_kill_the_listener():
    # Eén kapot pakket mag de listener niet doden -- hij draait dagenlang
    # onbewaakt en er komt van alles langs op een broadcastpoort.
    received: asyncio.Queue = asyncio.Queue()

    def on_packet(payload, source):
        if payload == b"boem":
            raise ValueError("stuk")
        received.put_nowait(payload)

    listener = await open_listener(port=0, bind="127.0.0.1", on_packet=on_packet)
    try:
        await send_to(listener.port, b"boem")
        await send_to(listener.port, b"nog steeds hier")
        payload = await asyncio.wait_for(received.get(), timeout=2)
    finally:
        listener.close()

    assert payload == b"nog steeds hier"


@pytest.mark.skipif(
    not hasattr(socket, "SO_REUSEPORT"),
    reason="SO_REUSEPORT bestaat niet op dit platform (Windows)",
)
async def test_sets_so_reuseport_so_a_debug_listener_can_join():
    listener = await open_listener(port=0, bind="127.0.0.1", on_packet=lambda payload, source: None)
    try:
        assert listener.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT) != 0
    finally:
        listener.close()
