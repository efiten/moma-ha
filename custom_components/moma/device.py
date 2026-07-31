"""Hoe een moma-apparaat als Home Assistant-device beschreven wordt.

Eén bron van waarheid, omdat er twee paden naar het device-register lopen: de
runtime maakt het device aan zodra een apparaat zich meldt, en de sensoren
hangen zich er via `DeviceInfo` aan vast. Zouden de `identifiers` op die twee
plekken ook maar iets uiteenlopen, dan verschijnen er twee devices naast elkaar
voor hetzelfde apparaat -- en dat is niet meer op te lossen zonder het register
met de hand op te schonen.
"""

from __future__ import annotations

from typing import Any

from .const import DOMAIN, MANUFACTURER, MODEL


def device_details(name: str) -> dict[str, Any]:
    """De velden die het device beschrijven, voor beide registratiepaden.

    `name` is de identiteit uit de broadcast: `Moma` plus het serienummer. Dat
    is een fabrieksidentiteit en geen door de gebruiker gekozen naam, dus hij is
    stabiel over herstarts en IP-wisselingen.
    """
    return {
        "identifiers": {(DOMAIN, name)},
        "name": name,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        # Een apparaat dat niet met de modelnaam begint levert geen serienummer
        # op. Dan liever leeg dan de volledige naam nog eens.
        "serial_number": name.removeprefix(MODEL) or None,
    }
