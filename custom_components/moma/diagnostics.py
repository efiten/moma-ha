"""Diagnostics voor moma.

Doel: een gebruiker met afwijkende hardware drukt één knop in plaats van door een
tcpdump-sessie gepraat te worden (ontwerpbeslissing 7). Voor een integratie die
onderhouden moet worden op hardware die de maintainer niet bezit, is dat het
verschil tussen onderhoudbaar en niet.

Serienummers en bronadressen worden geredigeerd. Zulke bestanden worden in
publieke issues geplakt; `name` is een fabrieksidentiteit en het bronadres wijst
het apparaat aan op het netwerk van de gebruiker.

De bron*poort* blijft wel staan. Die is efemeer en verraadt niets, terwijl hij
juist uitlegt waarom er niet op poortnummer gefilterd kan worden.
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

    return _redact(
        report,
        devices=runtime.tracker.devices,
        hosts=_source_hosts(runtime.recent_payloads),
    )


def _source_hosts(payloads: Iterable[dict[str, Any]]) -> set[str]:
    """De adressen waarvan pakketten kwamen, zonder poortnummer.

    `source` staat er als `adres:poort`. Alleen het adres is identificerend, dus
    daar splitsen we op -- vanaf rechts, zodat een IPv6-adres niet halverwege
    afgekapt wordt.
    """
    return {
        str(payload["source"]).rsplit(":", 1)[0]
        for payload in payloads
        if payload.get("source")
    }


def _redact(
    report: dict[str, Any], *, devices: Iterable[str], hosts: Iterable[str]
) -> dict[str, Any]:
    """Vervang elke apparaatnaam en elk bronadres door een teller.

    Bewust over het volledige rapport als tekst en niet veld voor veld: de naam
    komt op veel plekken voor -- als sleutel, in lijsten, en binnen de ruwe
    payloads -- en één vergeten plek maakt het redigeren zinloos.
    """
    text = json.dumps(report)

    for index, device in enumerate(sorted(devices), start=1):
        text = text.replace(device, f"DEVICE_{index}")

    # Nummeren op alfabet, zodat hetzelfde rapport altijd dezelfde labels geeft.
    # Vervangen van lang naar kort: zou `10.0.1.2` eerder vervangen worden dan
    # `10.0.1.23`, dan blijft van dat tweede adres een restje `3` staan.
    labels = {host: f"SOURCE_{index}" for index, host in enumerate(sorted(hosts), start=1)}
    for host in sorted(labels, key=len, reverse=True):
        text = text.replace(host, labels[host])

    return json.loads(text)
