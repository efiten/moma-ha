# Veldnamen in de moma-broadcast

Bedoeld om te delen met de ontwikkelaars van het apparaat.

De Home Assistant-integratie in deze repo leest de UDP-broadcast op poort 8484 en
maakt daar sensoren van **zonder per veld code te bevatten**. Het laatste deel van
een veldnaam, na de laatste underscore, bepaalt de eenheid, het sensortype en het
label in de interface:

```
grid_power_w  →  token "w"  →  watt, type "power", label "Grid power"
```

Het gevolg is dat er velden bij kunnen komen zonder dat de integratie een nieuwe
versie nodig heeft. Dat werkt alleen zolang het naamtoken klopt.

Zie [`protocol.md`](protocol.md) voor het protocol zoals waargenomen, en
[`ontwerpbeslissingen.md`](ontwerpbeslissingen.md) (beslissing 12) voor waarom
het zo opgezet is.

## Tokens die herkend worden

| Token | Eenheid | Sensortype | Voorbeeld |
|---|---|---|---|
| `_w` | watt | power | `pv_power_w` |
| `_kw` | kilowatt | power | `pv_power_kw` |
| `_wh` | wattuur | energy, cumulatief | `total_wh` |
| `_kwh` | kilowattuur | energy, cumulatief | `total_kwh` |
| `_v` | volt | voltage | `phase1_voltage_v` |
| `_a` | ampère | current | `phase1_current_a` |
| `_hz` | hertz | frequency | `frequency_hz` |
| `_c` | graden Celsius | temperature | `inverter_temp_c` |
| `_soc` | procent | battery | `battery_soc` |
| `_pct` of `_percent` | procent | — | `load_pct` |

Een onbekend token werkt ook: het veld wordt dan een kale meetwaarde zonder
eenheid en zonder type. Er gaat dus niets stuk, maar de weergave is minder goed.

Het token bepaalt ook het label. Een **eenheidstoken** verdwijnt uit de naam,
omdat de eenheid al naast de waarde staat: `grid_power_w` wordt "Grid power". Een
**semantisch token** blijft staan omdat het betekenis draagt: `battery_soc` wordt
"Battery SOC" en niet "Battery".

## Verzoeken

**1. Zet de eenheid altijd achteraan.** `w_grid_power` wordt niet herkend,
`grid_power_w` wel.

**2. Hernoem bestaande velden nooit — voeg alleen toe.** De veldnaam is de
identiteit van de sensor bij de eindgebruiker: hij zit in de `unique_id` en in de
`entity_id`. Een hernoeming maakt een nieuwe sensor aan en laat de oude achter met
alle opgebouwde historie eraan vast. Dat is voor de gebruiker niet te repareren
zonder handwerk.

**3. Let op onbedoelde tokens.** Een veld dat `phase_a` heet wordt gelezen als
ampère. Bedoel je fase A, noem het dan `phase_a_current_a` — iets waar het laatste
deel werkelijk de eenheid is.

**4. Laat cumulatieve tellers nooit terugvallen.** Als er ooit `_wh`- of
`_kwh`-velden bij komen: Home Assistant leest een dalende teller als een
meterreset en telt het verschil daarna opnieuw mee. Dat levert zichtbaar
verkeerde dag- en maandtotalen op. Ook niet resetten bij een firmware-update of
een herstart van het apparaat.

**5. Houd `version` op `1` zolang er alleen velden bijkomen.** De parser weigert
bewust pakketten met een onbekende versie: als de betekenis van bestaande velden
kan zijn veranderd, is geen data beter dan verkeerde data in iemands
energiegrafieken. Verhoog de versie dus alleen bij een echte
betekeniswijziging — dan weten wij dat we moeten kijken voor we hem ondersteunen.

## Tekenconventie

Opgegeven door de ontwikkelaars van het apparaat:

| Veld | Negatief | Positief |
|---|---|---|
| `grid_power_w` | injectie op het net | verbruik van het net |
| `battery_power_w` | ontladen | laden |

Voor de weergave verandert dit niets — de sensoren geven de waarde weer zoals hij
binnenkomt. Het gaat meespelen als er ooit kWh-tellers uit afgeleid worden, want
dan moeten verbruik en injectie apart geteld worden.

Verwachting bij nieuwe velden: **dezelfde regel**, positief is vermogen dat het
veld in gaat. Een `charger_power_w` van een laadpaal is dus positief tijdens het
laden van een auto.

## Wat we nog niet weten

Nog één ding, en dat is niet uit een opname af te lezen zolang het apparaat niet
herstart. Het wordt bijgehouden in
[`protocol.md`](protocol.md#openstaande-vragen).

**`sequence` bij een herstart** van het apparaat: begint de teller opnieuw bij 1,
of loopt hij door?

> Aangegeven: de teller herstart vrijwel zeker bij 1. Nog niet waargenomen.

Nuttig om te weten voor jullie kant: als de teller herstart, **laat dan bij
voorkeur ook de klok kloppen** voordat er weer gebroadcast wordt. De integratie
gebruikt `timestamp` om een herstart te onderscheiden van een verlaat pakket, dat
verworpen moet worden. Springt de klok achteruit — geen RTC, of NTP nog niet
gesynchroniseerd — dan valt hij terug op een tweede regel die een grote
terugval van de teller ook als herstart leest. Dat werkt, maar kost een paar
pakketten. Een kloppende klok bij het eerste pakket kost er nul.
