"""UDP-listener voor moma-broadcasts.

Deze laag interpreteert niets. Hij levert ruwe datagrammen af en laat het
parsen aan de laag erboven -- de recorder moet ook kunnen vastleggen wat we
(nog) niet begrijpen.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 8484

PacketHandler = Callable[[bytes, str], None]


class _MomaDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_packet: PacketHandler) -> None:
        self._on_packet = on_packet

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            self._on_packet(data, f"{addr[0]}:{addr[1]}")
        except Exception:  # noqa: BLE001 -- de listener mag nooit sneuvelen
            # Een broadcastpoort is van niemand. Wat hier binnenkomt kan van
            # alles zijn, en een fout in de verwerking mag de stroom niet
            # onderbreken.
            _LOGGER.exception("Fout bij het verwerken van een datagram van %s", addr)

    def error_received(self, exc: Exception) -> None:
        # Bij UDP betekent dit doorgaans een ICMP port-unreachable van een
        # eerdere verzending. Niet fataal.
        _LOGGER.debug("UDP-foutmelding ontvangen: %s", exc)


class MomaListener:
    """Een draaiende UDP-listener."""

    def __init__(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

    @property
    def socket(self) -> socket.socket:
        return self._transport.get_extra_info("socket")

    @property
    def port(self) -> int:
        """De poort waarop daadwerkelijk geluisterd wordt."""
        return self._transport.get_extra_info("sockname")[1]

    def close(self) -> None:
        self._transport.close()


async def open_listener(
    *,
    on_packet: PacketHandler,
    port: int = DEFAULT_PORT,
    bind: str = "0.0.0.0",
) -> MomaListener:
    """Start een listener.

    Bind standaard op `0.0.0.0`. Een socket die aan een specifiek interface-IP
    hangt ontvangt op Linux geen subnet-broadcast, en dat faalt stil: nul
    pakketten, geen foutmelding.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if hasattr(socket, "SO_REUSEPORT"):
        # Laat een debug-listener meeluisteren terwijl de integratie draait.
        # Bestaat niet op Windows; daar ontwikkel je, niet draai je.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    sock.setblocking(False)
    try:
        sock.bind((bind, port))
    except OSError:
        sock.close()
        raise

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _MomaDatagramProtocol(on_packet), sock=sock
    )

    return MomaListener(transport)
