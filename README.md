# MoMa voor Home Assistant

[![HACS: custom repository](https://img.shields.io/badge/HACS-custom%20repository-41BDF5.svg)](https://hacs.xyz)
[![Home Assistant 2025.1+](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41BDF5.svg)](https://www.home-assistant.io)
[![Licentie: MIT](https://img.shields.io/badge/licentie-MIT-blue.svg)](LICENSE)

Home Assistant-integratie voor de **MoMa** van
[Smart-E-Grid](https://smartegrid.be) — vermogen, batterijlading en
netfrequentie, rechtstreeks uit je eigen netwerk.

Er valt niets in te stellen. De MoMa maakt zichzelf bekend op je netwerk, dus je
hoeft geen IP-adres op te zoeken, geen wachtwoord in te vullen en geen account
aan te maken. Er gaat ook niets naar buiten: alles blijft lokaal.

## Installeren

Twee knoppen. De eerste voegt deze integratie toe aan HACS, de tweede stelt hem
in.

[![Open je Home Assistant en voeg deze repository toe aan HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=moma-ha&owner=efiten&category=Integration)

Klik **Download**, en **herstart Home Assistant**. Dan:

[![Open je Home Assistant en begin met het instellen van een nieuwe integratie.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=moma)

De poort staat voorgevuld op 8484 — laat die staan tenzij je weet dat hij
gewijzigd is. Je apparaat verschijnt binnen ongeveer vijf seconden.

> De knoppen vragen één keer het adres van jouw Home Assistant. Werken ze niet,
> gebruik dan de handmatige stappen hieronder.

<details>
<summary><b>Handmatig installeren</b></summary>

**Via HACS.** HACS → ⋮ rechtsboven → *Custom repositories* → URL
`https://github.com/efiten/moma-ha`, categorie **Integration** → *Add*. Zoek
daarna *Smart-E-Grid MoMa*, klik **Download** en herstart Home Assistant.

**Zonder HACS.** Kopieer de map `custom_components/moma/` uit deze repository
naar de map `custom_components/` in je Home Assistant-configuratie, en herstart.

**Instellen.** Settings → Devices & Services → **Add integration** →
*Smart-E-Grid MoMa*.

</details>

## Wat je krijgt

Eén apparaat per MoMa, met een sensor per meetwaarde:

| Sensor | Eenheid | Betekenis |
|---|---|---|
| Grid power | W | Uitwisseling met het net — **positief is verbruik, negatief is injectie** |
| Home power | W | Wat het huis verbruikt |
| PV power | W | Wat de zonnepanelen opwekken |
| Battery power | W | **Positief is laden, negatief is ontladen** |
| Battery SOC | % | Laadtoestand van de batterij |
| Frequency | Hz | Netfrequentie |

Krijgt je MoMa er later velden bij via een firmware-update, dan verschijnen die
vanzelf als sensor. Daar is geen nieuwe versie van deze integratie voor nodig.

## Er verschijnt geen apparaat, of geen sensoren

**Geen sensoren, maar wel een apparaat.** Dat is normaal bij een installatie die
nog niets doet. Een meetwaarde wordt pas een sensor zodra hij één keer iets
anders dan nul meldt — anders zou je vol staan met sensoren voor hardware die je
niet hebt. Je ziet hierover ook een melding bij *Instellingen → Reparaties*. Het
lost zichzelf op zodra de installatie gaat meten.

Wil je ze nu al zien: Devices & Services → **Smart-E-Grid MoMa** → *Configure* →
**Alle velden tonen**. Sensoren die zo ontstaan verdwijnen niet meer als je die
optie later weer uitzet.

**Helemaal geen apparaat.** Dan komt de aankondiging van de MoMa niet aan bij
Home Assistant. Meestal is dat het netwerk:

- Home Assistant moet in **hetzelfde netwerk** zitten als de MoMa. De
  aankondiging is een broadcast en komt niet door een router heen.
- Draait Home Assistant in Docker, dan moet dat met `--network host`. Op een
  bridge-netwerk komen broadcasts niet binnen.
- Een gastnetwerk of VLAN-scheiding tussen beide houdt het verkeer tegen.

**Alles onbeschikbaar geworden.** Na een minuut zonder bericht meldt de
integratie de sensoren als niet beschikbaar. Ze komen vanzelf terug zodra de
MoMa weer iets stuurt.

**Melden van een probleem.** Op de pagina van de integratie zit de knop
**Download diagnostics**. Dat bestand beschrijft precies wat er binnenkwam, met
het serienummer en het IP-adres eruit gehaald, dus het kan zo in een
[issue](https://github.com/efiten/moma-ha/issues).

## Meer lezen

- [`docs/ontwikkelen.md`](docs/ontwikkelen.md) — meewerken aan deze integratie:
  opzet, tests, en het opnamegereedschap
- [`docs/protocol.md`](docs/protocol.md) — hoe de MoMa zich aankondigt
- [`docs/ontwerpbeslissingen.md`](docs/ontwerpbeslissingen.md) — de gemaakte
  keuzes, met hun reden
- [`docs/veldnaamconventie.md`](docs/veldnaamconventie.md) — voor de
  ontwikkelaars van het apparaat: welke veldnamen vanzelf goed weergegeven worden

## Licentie

MIT — zie [LICENSE](LICENSE).
