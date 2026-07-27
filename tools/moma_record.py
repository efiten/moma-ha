#!/usr/bin/env python3
"""Neem moma UDP-broadcasts op en vat samen wat er langskwam.

Twee subcommando's:

    moma_record.py listen --out /share/moma/capture.jsonl
    moma_record.py summary /share/moma/capture.jsonl

`listen` schrijft elk datagram ongefilterd weg -- ook wat we nog niet
begrijpen. `summary` leest een opname terug en toont welke apparaten,
berichttypes en velden erin voorkwamen, met het waargenomen bereik.

Alleen standaardbibliotheek. Op Home Assistant OS volstaat `apk add python3`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
import time
from pathlib import Path


def _locate_protocol_package() -> None:
    """Zet de map met het `protocol`-pakket op sys.path.

    Werkt zowel vanuit de repo (`tools/` naast `custom_components/`) als in de
    add-on, waar het pakket naast dit script staat.
    """
    here = Path(__file__).resolve()
    candidates = (
        here.parent.parent / "custom_components" / "moma",
        here.parent,
    )
    for candidate in candidates:
        if (candidate / "protocol" / "__init__.py").is_file():
            sys.path.insert(0, str(candidate))
            return

    raise SystemExit(
        "Het protocol-pakket is niet gevonden. Verwacht in "
        + " of ".join(str(candidate) for candidate in candidates)
    )


_locate_protocol_package()

from protocol.ingest import Outcome, PacketIngest  # noqa: E402
from protocol.listener import DEFAULT_PORT, open_listener  # noqa: E402
from protocol.recorder import JsonlRecorder, replay  # noqa: E402
from protocol.watchdog import StallDetector  # noqa: E402


def _print_summary(ingest: PacketIngest) -> None:
    print(json.dumps(ingest.summary(), indent=2, ensure_ascii=False), flush=True)


def _describe(result, source: str) -> str:
    if result.outcome is Outcome.REJECTED:
        return f"[verworpen] {source}: {result.reason}"

    message = result.message
    if result.outcome is Outcome.STALE:
        return f"[verlaat] {source}: {message.name} seq={message.sequence}"

    values = " ".join(f"{key}={value}" for key, value in message.fields.items())
    return f"{message.name} {message.type} seq={message.sequence} {values}"


def _install_stop_handlers(stop: asyncio.Event) -> None:
    """Zorg dat SIGTERM en SIGINT netjes afronden.

    Supervisor stopt een add-on met SIGTERM. Zonder handler eindigt het proces
    meteen en zie je de slotinventaris nooit. Op Windows bestaat
    `add_signal_handler` niet; daar vangt KeyboardInterrupt het af.
    """
    loop = asyncio.get_running_loop()
    for name in ("SIGTERM", "SIGINT"):
        received = getattr(signal, name, None)
        if received is None:
            continue
        try:
            loop.add_signal_handler(received, stop.set)
        except (NotImplementedError, RuntimeError):
            pass


async def _watch_for_stalls(detector: StallDetector, timeout: float) -> None:
    """Waarschuw wanneer de stroom pakketten stilvalt, en wanneer hij terugkomt.

    Zonder dit blijft een doof geworden listener tevreden draaien: er crasht
    niets, Supervisor herstart niets, en je merkt het pas als je een opname
    opent die na een uur ophield.
    """
    interval = max(1.0, min(5.0, timeout / 4))
    reported = False

    while True:
        await asyncio.sleep(interval)
        now = time.monotonic()

        if detector.is_stalled(now=now):
            if not reported:
                reported = True
                print(
                    f"[stilstand] al {detector.quiet_for(now=now):.0f}s geen pakket ontvangen",
                    flush=True,
                )
        elif reported:
            reported = False
            print("[herstel] pakketten komen weer binnen", flush=True)


async def _listen(args: argparse.Namespace) -> int:
    ingest = PacketIngest()
    last_report = time.monotonic()
    stop = asyncio.Event()
    detector = StallDetector(timeout=args.stall_timeout, now=time.monotonic())

    recorder = JsonlRecorder(args.out) if args.out else None
    if recorder is not None:
        recorder.__enter__()

    def handle(payload: bytes, source: str) -> None:
        nonlocal last_report

        detector.packet_received(now=time.monotonic())

        # Vastleggen voor het interpreteren: de opname moet ook bevatten wat we
        # niet begrijpen, want daarvoor draait hij.
        if recorder is not None:
            recorder.record(payload, source=source, received_at=time.time())

        result = ingest.handle(payload)

        if not args.quiet:
            print(_describe(result, source), flush=True)

        now = time.monotonic()
        if args.report_every and now - last_report >= args.report_every:
            last_report = now
            _print_summary(ingest)

    listener = await open_listener(on_packet=handle, port=args.port, bind=args.bind)
    _install_stop_handlers(stop)

    print(
        f"luistert op {args.bind}:{listener.port} -> {args.out or '(niet opgenomen)'}"
        " -- Ctrl-C om te stoppen",
        flush=True,
    )

    watchdog = (
        asyncio.create_task(_watch_for_stalls(detector, args.stall_timeout))
        if args.stall_timeout
        else None
    )

    try:
        await stop.wait()
    finally:
        if watchdog is not None:
            watchdog.cancel()
        listener.close()
        if recorder is not None:
            recorder.close()
        _print_summary(ingest)

    return 0


def _summary(args: argparse.Namespace) -> int:
    ingest = PacketIngest()
    for packet in replay(args.capture):
        ingest.handle(packet.payload)
    _print_summary(ingest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    listen = subcommands.add_parser("listen", help="opnemen vanaf het netwerk")
    listen.add_argument("--port", type=int, default=DEFAULT_PORT)
    listen.add_argument(
        "--bind",
        default="0.0.0.0",
        help="standaard 0.0.0.0; een specifiek interface-IP ontvangt geen broadcast",
    )
    listen.add_argument("--out", help="pad naar het JSONL-bestand")
    listen.add_argument("--quiet", action="store_true", help="geen regel per pakket")
    listen.add_argument(
        "--report-every",
        type=int,
        default=0,
        metavar="SECONDEN",
        help="periodiek een inventaris tonen (0 = alleen bij afsluiten)",
    )
    listen.add_argument(
        "--stall-timeout",
        type=int,
        default=60,
        metavar="SECONDEN",
        help=(
            "waarschuwen na zoveel seconden zonder pakket (0 = uit); "
            "standaard 60, ongeveer twaalf gemiste intervallen"
        ),
    )

    summary = subcommands.add_parser("summary", help="een opname samenvatten")
    summary.add_argument("capture", help="pad naar een eerder opgenomen JSONL-bestand")

    args = parser.parse_args(argv)

    if args.command == "summary":
        return _summary(args)

    try:
        return asyncio.run(_listen(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
