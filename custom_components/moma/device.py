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

from .const import DOMAIN, MANUFACTURER, MODEL, NAME_PREFIX


def device_details(name: str) -> dict[str, Any]:
    """De velden die het device beschrijven, voor beide registratiepaden.

    `name` is de identiteit uit de broadcast: `Moma` plus het serienummer. Dat
    is een fabrieksidentiteit en geen door de gebruiker gekozen naam, dus hij is
    stabiel over herstarts en IP-wisselingen.

    Let op het verschil tussen de twee keren dat die naam hier voorkomt. In
    `identifiers` staat hij **onveranderd**, want dat is de sleutel waar het
    device en de `unique_id` van zijn entiteiten aan hangen. In `name` staat de
    weergavevariant, en die mag afwijken.
    """
    return {
        "identifiers": {(DOMAIN, name)},
        "name": display_device_name(name),
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        # Een apparaat dat niet met het bekende voorvoegsel begint levert geen
        # serienummer op. Dan liever leeg dan de volledige naam nog eens.
        "serial_number": name.removeprefix(NAME_PREFIX) or None,
    }


def display_device_name(name: str) -> str:
    """De apparaatnaam in de schrijfwijze van de fabrikant.

    Het apparaat broadcast `Moma001539`; de fabrikant schrijft het product als
    `MoMa`. Dat verschil is puur cosmetisch, dus het wordt hier omgezet en niet
    in de identiteit. Een naam die het voorvoegsel niet heeft blijft ongemoeid --
    dat kan een firmwarevariant zijn, en er is geen reden te gokken.
    """
    if not name.startswith(NAME_PREFIX):
        return name

    return MODEL + name.removeprefix(NAME_PREFIX)
