"""Bijhouden welke velden een sensor verdienen.

Het apparaat stuurt alle velden, ook die van hardware die niet aanwezig is. Een
`battery_soc` die permanent nul blijft is geen meting maar ruis, en hoort geen
entiteit te worden.

De regel is daarom: een veld activeert bij zijn eerste waarde die niet nul is.
Activering is eenrichtingsverkeer -- zonnepanelen staan 's nachts op nul, en de
sensor mag dan niet verdwijnen. Daarom is `state()` bedoeld om te bewaren en bij
het opstarten weer mee te geven.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .messages import MomaMessage

# `online` zegt niets over een meting; de beschikbaarheid van een apparaat
# bepalen we aan de hand van de vraag of er nog pakketten binnenkomen.
IGNORED_FIELDS = frozenset({"online"})


class FieldActivation:
    """Weet per apparaat welke velden ooit een echte waarde hadden."""

    def __init__(
        self,
        *,
        ignored: Iterable[str] = IGNORED_FIELDS,
        active: Mapping[str, Iterable[str]] | None = None,
        require_value: bool = True,
    ) -> None:
        """`require_value=False` activeert elk veld bij de eerste keer zien.

        Bedoeld voor een testinstallatie: bij een inactief apparaat staat alles
        op nul, activeert er niets, en krijg je een device zonder sensoren. Dat
        lijkt kapot terwijl het correct is. Genegeerde velden blijven ook dan
        genegeerd.
        """
        self._ignored = frozenset(ignored)
        self._require_value = require_value
        self._active: dict[str, set[str]] = {
            device: set(fields) for device, fields in (active or {}).items()
        }

    def observe(self, message: MomaMessage) -> list[str]:
        """Verwerk een bericht en geef de velden terug die nú pas activeren.

        Alleen nieuwe activeringen komen terug, zodat de aanroeper er
        rechtstreeks entiteiten voor kan aanmaken zonder dubbels te maken.
        """
        active = self._active.setdefault(message.name, set())

        newly_activated = [
            name
            for name, value in message.fields.items()
            if name not in self._ignored
            and name not in active
            and (not self._require_value or self._is_real(value))
        ]
        active.update(newly_activated)

        return newly_activated

    def is_active(self, device: str, field: str) -> bool:
        return field in self._active.get(device, ())

    def forget(self, device: str) -> None:
        """Wis wat er over dit apparaat onthouden is.

        Nodig om een apparaat uit Home Assistant te kunnen verwijderen. Bleef de
        activeringsstatus staan, dan komen de sensoren bij het eerstvolgende
        pakket meteen terug en lijkt de verwijderknop stuk.

        Een onbekend apparaat vergeten mag: de aanroeper weet niet of dit
        apparaat ooit een veld activeerde.
        """
        self._active.pop(device, None)

    def state(self) -> dict[str, list[str]]:
        """Momentopname om te bewaren tussen herstarts."""
        return {device: sorted(fields) for device, fields in self._active.items() if fields}

    @staticmethod
    def _is_real(value: object) -> bool:
        """Of deze waarde bewijst dat het veld in gebruik is.

        Waarheidswaarde volstaat: 0, 0.0 en False betekenen "niets aan de hand
        of niet aanwezig", elk ander getal is een meting -- ook een negatieve,
        want injectie op het net is net zo goed een meting als afname.
        """
        return bool(value)
