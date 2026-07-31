"""Toestand per apparaat, afgeleid uit de pakketstroom.

Zet datagrammen om in "wat is de laatste stand van apparaat X" plus de twee
gebeurtenissen waar een consument op moet reageren: er is een nieuw apparaat, en
er zijn velden voor het eerst geactiveerd.

Bevat geen Home Assistant-code. De sensorlaag hangt hier bovenop en blijft
daardoor dun, en deze logica is zonder Home Assistant te testen.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .activation import FieldActivation
from .ingest import Outcome, PacketIngest


@dataclass(frozen=True)
class DeviceUpdate:
    """Het resultaat van één verwerkt pakket."""

    device: str
    is_new_device: bool
    activated_fields: tuple[str, ...]
    values: Mapping[str, Any]


@dataclass
class DeviceTracker:
    """Houdt de laatste waarden per apparaat bij."""

    show_all_fields: bool = False
    activation: FieldActivation | None = None
    _values: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.activation is None:
            self.activation = FieldActivation(require_value=not self.show_all_fields)
        self._ingest = PacketIngest(activation=self.activation)

    def handle(self, payload: bytes) -> DeviceUpdate | None:
        """Verwerk één datagram.

        Geeft `None` terug wanneer het pakket geen geldig moma-bericht is of
        achterhaald is. In beide gevallen mag de toestand niet wijzigen: een
        verlaat pakket zou vermogenswaarden terug in de tijd laten springen.
        """
        result = self._ingest.handle(payload)
        if result.outcome is not Outcome.ACCEPTED:
            return None

        message = result.message
        is_new_device = message.name not in self._values
        self._values.setdefault(message.name, {}).update(message.fields)

        return DeviceUpdate(
            device=message.name,
            is_new_device=is_new_device,
            activated_fields=result.activated_fields,
            values=self.values_for(message.name),
        )

    @property
    def devices(self) -> tuple[str, ...]:
        return tuple(self._values)

    def values_for(self, device: str) -> Mapping[str, Any]:
        return dict(self._values.get(device, {}))

    def forget(self, device: str) -> None:
        """Vergeet dit apparaat volledig.

        Toestand per apparaat zit op vier plekken -- de laatste waarden hier, en
        de activeringsstatus, de volgordebewaking en de inventaris in de
        ingestlaag. Blijft er ergens iets staan, dan is het apparaat niet echt
        weg: het komt terug als bekend, of zijn naam verschijnt nog in
        diagnostics.
        """
        self._values.pop(device, None)
        self._ingest.forget(device)

    def activation_state(self) -> dict[str, list[str]]:
        """Momentopname om te bewaren tussen herstarts."""
        return self.activation.state()

    def summary(self) -> dict[str, Any]:
        """Diagnostische samenvatting van de verwerkte stroom."""
        return self._ingest.summary()
