"""Eén datagram van bytes naar een verwerkt resultaat.

Bundelt parsen, volgordebewaking en inventarisatie, zodat live meeluisteren en
het terugspelen van een opname gegarandeerd dezelfde uitkomst geven. Toen dat
twee losse implementaties waren, liepen ze uiteen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .activation import FieldActivation
from .messages import InvalidPacket, MomaMessage, parse_packet
from .ordering import SequenceTracker
from .survey import ProtocolSurvey


class Outcome(Enum):
    """Wat er met een datagram gebeurd is."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    """Geen geldig moma-pakket. Poort 8484 is van niemand."""
    STALE = "stale"
    """Wel geldig, maar achterhaald: verlaat of dubbel bezorgd."""


@dataclass(frozen=True)
class IngestResult:
    outcome: Outcome
    message: MomaMessage | None = None
    reason: str | None = None
    activated_fields: tuple[str, ...] = ()
    """Velden die met dít pakket voor het eerst een waarde kregen."""


class PacketIngest:
    """Verwerkt datagrammen en houdt bij wat er langskwam."""

    def __init__(self, *, activation: FieldActivation | None = None) -> None:
        self._tracker = SequenceTracker()
        self._survey = ProtocolSurvey()
        # Injecteerbaar zodat een bewaarde activeringsstatus meegegeven kan
        # worden: na een herstart mogen bestaande sensoren niet opnieuw als
        # nieuw gemeld worden.
        self._activation = activation if activation is not None else FieldActivation()
        self._rejected = 0
        self._stale = 0

    def handle(self, payload: bytes) -> IngestResult:
        try:
            message = parse_packet(payload)
        except InvalidPacket as err:
            self._rejected += 1
            return IngestResult(Outcome.REJECTED, reason=str(err))

        if not self._tracker.accept(message):
            self._stale += 1
            return IngestResult(Outcome.STALE, message=message)

        self._survey.observe(message)
        return IngestResult(
            Outcome.ACCEPTED,
            message=message,
            activated_fields=tuple(self._activation.observe(message)),
        )

    def forget(self, name: str) -> None:
        """Wis alle toestand van dit apparaat, in alle drie de onderdelen."""
        self._tracker.forget(name)
        self._survey.forget(name)
        self._activation.forget(name)

    def summary(self) -> dict[str, Any]:
        summary = self._survey.summary()
        summary["rejected_packets"] = self._rejected
        summary["stale_packets"] = self._stale
        summary["lost_packets"] = {
            device: self._tracker.lost_for(device) for device in summary["devices"]
        }
        # Welke velden een sensor zouden worden. Wat hier ontbreekt bleef de
        # hele opname op nul en hoort dus bij hardware die er niet is.
        summary["active_fields"] = self._activation.state()
        return summary
