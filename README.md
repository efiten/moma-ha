# moma-ha

Home Assistant-integratie voor apparaten die het **moma**-protocol via UDP
broadcasten — energiedata (vermogen, SOC, frequentie) van onder meer een
laadpaal.

> **Status.** De protocollaag en de recorder werken. De Home
> Assistant-integratie zelf (config flow, entities) is nog niet gebouwd —
> daarvoor wachten we op een opname van een actief apparaat.

## Nu al bruikbaar: de recorder

Het apparaat is pas na 1 augustus 2026 volledig actief. Tot dan verzamelt de
recorder wat er langskomt, zodat het datamodel op echte data gebaseerd wordt in
plaats van op een capture waarin alles op nul stond.

Snel meekijken vanaf de Home Assistant-host (*Advanced SSH & Web
Terminal*-add-on, `apk add python3`):

```sh
python3 tools/moma_record.py listen --out /share/moma/capture.jsonl
```

Voor een opname die dagen onbewaakt draait, zie
[`addon/moma-recorder/`](addon/moma-recorder/README.md).

Een opname samenvatten — welke apparaten, berichttypes en velden erin zaten,
met het waargenomen bereik per veld:

```sh
python3 tools/moma_record.py summary /share/moma/capture.jsonl
```

## Installeren via HACS

> Nog niet zinvol — de integratie doet nog niets. Dit staat hier zodat de
> structuur klopt zodra de sensorlaag er is.

HACS → ⋮ → **Custom repositories** → `https://github.com/efiten/moma-ha`,
categorie **Integration**. Daarna installeren en Home Assistant herstarten.

## Ontwikkelen

```sh
python -m venv .venv
.venv/Scripts/python -m pip install pytest pytest-asyncio
.venv/Scripts/python -m pytest
```

De tests van laag 1 draaien zonder Home Assistant. `pyproject.toml` zet
`custom_components/moma` op het pad zodat ze `protocol.*` rechtstreeks
importeren, buiten `custom_components/moma/__init__.py` om — dat bestand gaat
straks homeassistant importeren en zou die onafhankelijkheid breken.

## Doel

Een generieke, installeerbare integratie die zonder configuratie meerdere
moma-apparaten op hetzelfde netwerk herkent en als Home Assistant-devices
aanbiedt, inclusief koppeling met het Energy dashboard. Uiteindelijk te
distribueren via HACS.

## Opzet

De integratie splitst strikt in twee lagen:

| Laag | Locatie | Verantwoordelijkheid |
|---|---|---|
| 1 — transport & protocol | `custom_components/moma/protocol/` | UDP-socket, parsen, valideren, volgorde bewaken. **Geen Home Assistant-imports**, volledig testbaar met bytestrings. |
| 2 — Home Assistant | `custom_components/moma/` | Config flow, devices, entities, availability. |

Laag 1 staat bewust *binnen* de integratiemap: HACS distribueert alleen
`custom_components/moma/`, dus een zustermap op repo-niveau zou nooit bij de
gebruiker terechtkomen. `tools/` en `tests/` importeren hem vanaf de repo-root
als `custom_components.moma.protocol`.

## Mappen

```
custom_components/moma/   de integratie (het enige dat HACS uitlevert)
tools/                    standalone recorder, draait op de HA-host
addon/moma-recorder/      lokale Home Assistant-add-on als ontwikkelharnas
tests/                    pytest, draait tegen fixtures
fixtures/                 geanonimiseerd capture-corpus
docs/                     protocolonderzoek en ontwerpdocumenten
```

`addon/moma-recorder/` is géén Supervisor-add-onrepository. Het is een
ontwikkelharnas dat je naar `/addons/` op de HA-machine kopieert.

## Data en privacy

Ruwe captures bevatten huishoudelijke telemetrie en horen **niet** in git —
`captures/` staat in `.gitignore`. Alleen handmatig geanonimiseerde monsters
gaan naar `fixtures/`: serienummers vervangen, timestamps genormaliseerd.

Deze repo is privé maar wordt later publiek gezet. De volledige git-historie
wordt dan mee zichtbaar; er is geen tweede kans om dit recht te zetten.

## Documentatie

- [`docs/protocol.md`](docs/protocol.md) — het moma-protocol zoals waargenomen
- [`docs/ontwerpbeslissingen.md`](docs/ontwerpbeslissingen.md) — de genomen
  beslissingen, met hun reden

## Licentie

MIT — zie [LICENSE](LICENSE).
