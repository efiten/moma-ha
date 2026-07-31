# Meewerken aan deze integratie

Alles wat een gebruiker niet nodig heeft. Voor installeren en gebruiken, zie de
[README](../README.md).

## Doel

Een generieke, installeerbare integratie die zonder configuratie meerdere
MoMa-apparaten op hetzelfde netwerk herkent en als Home Assistant-devices
aanbiedt, inclusief koppeling met het Energy dashboard.

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
custom_components/moma/brand/  icoon, wordt door de integratie zelf meegeleverd
tools/                    standalone recorder, draait op de HA-host
addon/moma-recorder/      lokale Home Assistant-add-on als ontwikkelharnas
tests/                    pytest, draait tegen fixtures
fixtures/                 geanonimiseerd capture-corpus
docs/                     protocolonderzoek en ontwerpdocumenten
```

`addon/moma-recorder/` is géén Supervisor-add-onrepository. Het is een
ontwikkelharnas dat je naar `/addons/` op de HA-machine kopieert.

## Tests

De testsuite is gesplitst langs de laaggrens.

**Laag 1** (`tests/protocol/`) heeft Home Assistant niet nodig en draait overal,
ook op Windows:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install pytest pytest-asyncio
.venv/Scripts/python -m pytest tests/protocol
```

`pyproject.toml` zet `custom_components/moma` op het pad zodat deze tests
`protocol.*` rechtstreeks importeren, buiten `custom_components/moma/__init__.py`
om — dat bestand importeert homeassistant en zou die onafhankelijkheid breken.

**Laag 2** (`tests/integration/`) heeft Home Assistant nodig, en dat testharnas
is Unix-only: het importeert `fcntl`. Op Windows draait dit dus via WSL:

```sh
wsl -- bash scripts/test.sh -q
```

> Installeer `pytest-homeassistant-custom-component` **niet** in een
> Windows-venv. pytest laadt die plugin automatisch, waarna zelfs de
> laag-1-tests omvallen op `fcntl`.

Eenmalig in WSL, omdat Ubuntu `venv` niet standaard meelevert:

```sh
sudo apt install -y python3.14-venv
```

CI draait beide lagen als aparte jobs. De laag-1-job installeert Home Assistant
bewust niet, zodat hij omvalt als er ooit een HA-import in laag 1 sluipt.

## De recorder

> **Niet nodig om de integratie te gebruiken.** Dit is een ontwikkelharnas voor
> protocolonderzoek. In normaal gebruik ontvangt de integratie de broadcast zelf,
> en levert de knop **Download diagnostics** op de device-pagina de laatste ruwe
> payloads met het serienummer geredigeerd. Laat de recorder niet permanent
> meelopen: hij claimt dezelfde poort als de integratie.

Snel meekijken vanaf de Home Assistant-host, via de *Advanced SSH & Web
Terminal*-add-on (die heeft `python3` al aan boord):

```sh
python3 tools/moma_record.py listen --out /share/moma/capture.jsonl
```

Voor een opname die dagen onbewaakt draait, zie
[`addon/moma-recorder/`](../addon/moma-recorder/README.md).

Een opname samenvatten — welke apparaten, berichttypes en velden erin zaten,
met het waargenomen bereik per veld:

```sh
python3 tools/moma_record.py summary /share/moma/capture.jsonl
```

## Problemen opsporen op een draaiende installatie

**Er is geen logbestand meer.** Op Home Assistant OS schrijft Core sinds 2026
geen `/config/home-assistant.log`; alles gaat naar journald. Lees mee via
*Settings → System → Logs*.

Uitgebreide logging aanzetten zonder herstart — *Developer tools → Actions*:

```yaml
action: logger.set_level
data:
  custom_components.moma: debug
```

Permanent, in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.moma: debug
```

Waarschuwingen en fouten verschijnen ook zonder debug-niveau in het
systeemlogboek. Blijft het daar stil terwijl er niets gebeurt, dan komt er
waarschijnlijk niets binnen op de poort.

## Versies

Er zijn bewust nog **geen releases**. HACS volgt dan de `main`-branch, zodat een
`git push` direct beschikbaar is. Zodra er één release bestaat biedt HACS die
aan en moet je expliciet *main* kiezen om nieuwere code te krijgen — tijdens
ontwikkelen is dat een valkuil.

Het versienummer in `custom_components/moma/manifest.json` is wat HACS toont. Een
release-workflow weigert een release waarvan de git-tag daarvan afwijkt.

## Het icoon

De integratie levert zijn eigen icoon mee, in `custom_components/moma/brand/`.
Sinds **Home Assistant 2026.3** hebben lokale merkafbeeldingen voorrang op de
[brands-CDN](https://brands.home-assistant.io); Home Assistant biedt ze aan op
`/api/brands/integration/moma/icon.png`.

Twee bestanden volstaan: `icon.png` (256×256) en `icon@2x.png` (512×512). Er is
bewust géén `logo.png` — ontbreekt die, dan serveert Home Assistant het icoon,
en de zwarte merknaam zou op een donker thema onleesbaar worden.

Op Home Assistant ouder dan 2026.3 werkt dit niet en blijft de integratiepagina
een grijs vakje tonen. Daarvoor zou een PR naar
[`home-assistant/brands`](https://github.com/home-assistant/brands) nodig zijn,
waar de map `custom_integrations/` voor bestaat — inmiddels als legacy aangemerkt,
juist omdat deze route hem vervangt.

## Data en privacy

Ruwe captures bevatten huishoudelijke telemetrie en horen **niet** in git —
`captures/` staat in `.gitignore`. Alleen handmatig geanonimiseerde monsters
gaan naar `fixtures/`: serienummers vervangen, timestamps genormaliseerd.

Deze repository is publiek, inclusief de volledige historie. Wat hier ooit in
komt is niet meer weg te halen.
