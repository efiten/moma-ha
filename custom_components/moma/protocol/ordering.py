"""Volgordebewaking voor een stroom UDP-pakketten.

UDP levert niet in volgorde en verliest pakketten zonder melding. Zonder deze
laag springen vermogenswaarden terug in de tijd en ontstaan zaagtanden in de
statistieken van Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass

from .messages import MomaMessage

# Hoeveel de teller mag terugvallen voordat we het als een herstart lezen in
# plaats van als een verlaat pakket. UDP levert pakketten door elkaar met een
# paar plaatsen verschil; honderden plaatsen terug is geen herordening.
RESET_THRESHOLD = 10


@dataclass
class _DeviceState:
    sequence: int
    timestamp: int
    lost: int = 0


class SequenceTracker:
    """Beslist per apparaat of een pakket verwerkt mag worden."""

    def __init__(self) -> None:
        self._devices: dict[str, _DeviceState] = {}

    def accept(self, message: MomaMessage) -> bool:
        """Geef terug of dit pakket het nieuwste is voor zijn apparaat.

        Een lagere `sequence` is normaal gesproken een verlaat pakket en wordt
        verworpen. Uitzondering: als de `timestamp` juist vooruit is gesprongen,
        heeft het apparaat herstart en begint de teller opnieuw. Zonder die
        uitzondering zou de integratie na elke herstart permanent stil vallen.
        """
        known = self._devices.get(message.name)

        if known is None:
            self._devices[message.name] = _DeviceState(message.sequence, message.timestamp)
            return True

        if message.sequence > known.sequence:
            known.lost += message.sequence - known.sequence - 1
            known.sequence = message.sequence
            known.timestamp = message.timestamp
            return True

        if message.timestamp > known.timestamp:
            # Teller terug, klok vooruit: herstart. Geen verlies, de reeks
            # begint gewoon opnieuw.
            known.sequence = message.sequence
            known.timestamp = message.timestamp
            return True

        if known.sequence - message.sequence >= RESET_THRESHOLD:
            # Teller ver terug en de klok ook: een herstart zonder betrouwbare
            # tijd. Dat gebeurt als het apparaat geen RTC heeft of NTP nog niet
            # gesynchroniseerd is.
            #
            # Zonder deze uitweg zou de tracker elk pakket weigeren tot de teller
            # weer boven de oude waarde uitkomt. Bij een teller die op 500 stond
            # en vijf seconden per pakket is dat veertig minuten stilte, zonder
            # dat er iets in het log verschijnt.
            known.sequence = message.sequence
            known.timestamp = message.timestamp
            return True

        return False

    def lost_for(self, name: str) -> int:
        """Aantal pakketten dat voor dit apparaat ontbrak in de reeks."""
        known = self._devices.get(name)
        return known.lost if known else 0

    def forget(self, name: str) -> None:
        """Vergeet de laatst geziene positie van dit apparaat.

        Zonder dit zou een apparaat dat na verwijderen terugkomt zijn oude
        `sequence` tegenkomen, en meldt het eerste pakket een gat van honderden
        pakketten dat er nooit was.
        """
        self._devices.pop(name, None)
