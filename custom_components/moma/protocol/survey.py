"""Inventariseert wat er feitelijk over de lijn kwam.

Dagenlang opnemen levert een bestand met tienduizenden regels. Deze inventaris
vat samen welke apparaten, berichttypes en velden daarin voorkwamen, met het
waargenomen bereik per veld. Dat bereik beantwoordt twee vragen die je anders
moet gokken: de schaal van een veld en zijn tekenconventie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .messages import MomaMessage


@dataclass
class _FieldObservation:
    count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    example: Any = None

    def add(self, value: Any) -> None:
        self.count += 1

        # bool is een subklasse van int; een aan/uit-veld heeft geen bereik.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if self.example is None:
                self.example = value
            return

        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def as_dict(self) -> dict[str, Any]:
        observed: dict[str, Any] = {"count": self.count}
        if self.minimum is not None:
            observed["min"] = self.minimum
            observed["max"] = self.maximum
        if self.example is not None:
            observed["example"] = self.example
        return observed


@dataclass
class ProtocolSurvey:
    """Verzamelt welke velden en berichttypes zijn langsgekomen."""

    packets: int = 0
    devices: set[str] = field(default_factory=set)
    _fields: dict[str, dict[str, _FieldObservation]] = field(default_factory=dict)

    def observe(self, message: MomaMessage) -> None:
        self.packets += 1
        self.devices.add(message.name)

        # Velden per berichttype bijhouden: een `meter`-bericht heeft andere
        # velden dan een `state`-bericht, en dat verschil moet zichtbaar zijn.
        per_type = self._fields.setdefault(message.type, {})
        for name, value in message.fields.items():
            per_type.setdefault(name, _FieldObservation()).add(value)

    def forget(self, name: str) -> None:
        """Haal dit apparaat uit de inventaris.

        Niet alleen voor de netheid: diagnostics redigeert apparaatnamen op basis
        van wat de tracker kent. Bleef een verwijderd apparaat hier staan, dan
        verscheen zijn serienummer ongeredigeerd in `summary["devices"]`.

        De veldwaarnemingen zijn per berichttype en niet per apparaat, dus daar
        valt niets te scheiden. `packets` blijft ook staan: dat is het aantal
        verwerkte datagrammen en niet iets van één apparaat.
        """
        self.devices.discard(name)

    def summary(self) -> dict[str, Any]:
        return {
            "packets": self.packets,
            "devices": sorted(self.devices),
            "types": sorted(self._fields),
            "fields": {
                message_type: {
                    name: observation.as_dict() for name, observation in sorted(fields.items())
                }
                for message_type, fields in sorted(self._fields.items())
            },
        }
