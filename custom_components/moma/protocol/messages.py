"""Parsen en valideren van moma-pakketten."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

PROTOCOL_NAME = "moma"

# Uitbreiden zodra een nieuwe versie waargenomen en begrepen is. Een onbekende
# versie stilzwijgend accepteren is gevaarlijker dan hem weigeren: velden kunnen
# van betekenis veranderd zijn, en dan publiceer je verkeerde meetwaarden in
# plaats van geen.
SUPPORTED_VERSIONS = frozenset({1})

_ENVELOPE_FIELDS = ("name", "sequence", "timestamp", "type")

# Alles buiten deze sleutels beschouwen we als meetwaarde. Zo levert nieuwe
# firmware automatisch nieuwe velden op zonder codewijziging.
_ENVELOPE_KEYS = frozenset({"protocol", "version", *_ENVELOPE_FIELDS})


class InvalidPacket(Exception):
    """Het datagram is geen bruikbaar moma-pakket.

    Poort 8484 is niet exclusief van deze integratie. Alles wat hier
    langskomt en niet aan het protocol voldoet hoort verworpen te worden,
    niet gelogd als fout.
    """


@dataclass(frozen=True)
class MomaMessage:
    """Een gedecodeerd moma-pakket.

    `fields` bevat de meetwaarden zonder envelope; `raw` het volledige
    document zoals ontvangen, voor diagnostics en de recorder.
    """

    version: int
    type: str
    name: str
    sequence: int
    timestamp: int
    fields: Mapping[str, Any]
    raw: Mapping[str, Any]


def parse_packet(payload: bytes) -> MomaMessage:
    """Decodeer één UDP-datagram tot een MomaMessage.

    Raises:
        InvalidPacket: bij alles wat geen geldig moma-pakket is.
    """
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as err:
        raise InvalidPacket(f"geen geldige JSON: {err}") from err

    if not isinstance(document, dict):
        raise InvalidPacket(f"verwachtte een JSON-object, kreeg {type(document).__name__}")

    if document.get("protocol") != PROTOCOL_NAME:
        raise InvalidPacket(f"vreemd protocol: {document.get('protocol')!r}")

    version = document.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise InvalidPacket(f"niet-ondersteunde protocolversie: {version!r}")

    missing = [field for field in _ENVELOPE_FIELDS if field not in document]
    if missing:
        raise InvalidPacket(f"envelope mist velden: {', '.join(missing)}")

    return MomaMessage(
        version=version,
        type=document["type"],
        name=document["name"],
        sequence=document["sequence"],
        timestamp=document["timestamp"],
        fields=MappingProxyType(
            {key: value for key, value in document.items() if key not in _ENVELOPE_KEYS}
        ),
        raw=MappingProxyType(document),
    )
