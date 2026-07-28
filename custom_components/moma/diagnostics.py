"""Diagnostics voor moma.

Doel: een gebruiker met afwijkende hardware drukt één knop in plaats van door een
tcpdump-sessie gepraat te worden (ontwerpbeslissing 7). Voor een integratie die
onderhouden moet worden op hardware die de maintainer niet bezit, is dat het
verschil tussen onderhoudbaar en niet.

Serienummers worden geredigeerd. Zulke bestanden worden in publieke issues
geplakt, en `name` is een fabrieksidentiteit.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from homeassistant.core import HomeAssistant

from . import MomaConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MomaConfigEntry
) -> dict[str, Any]:
    """Stel een rapport samen over de ontvangen stroom."""
    runtime = entry.runtime_data

    report: dict[str, Any] = {
        "port": runtime.port,
        "show_all_fields": runtime.show_all_fields,
        "available": runtime.available,
        "summary": runtime.tracker.summary(),
        "values": {
            device: runtime.tracker.values_for(device) for device in runtime.tracker.devices
        },
        "recent_payloads": runtime.recent_payloads,
    }

    return _redact_devices(report, runtime.tracker.devices)


def _redact_devices(report: dict[str, Any], devices: Iterable[str]) -> dict[str, Any]:
    """Vervang elke apparaatnaam door een teller.

    Bewust over het volledige rapport als tekst en niet veld voor veld: de naam
    komt op veel plekken voor -- als sleutel, in lijsten, en binnen de ruwe
    payloads -- en één vergeten plek maakt het redigeren zinloos.
    """
    text = json.dumps(report)

    for index, device in enumerate(sorted(devices), start=1):
        text = text.replace(device, f"DEVICE_{index}")

    return json.loads(text)
