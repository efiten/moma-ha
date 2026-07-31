# Het moma-protocol

Waargenomen op 2026-07-27 met `tcpdump` op een Home Assistant OS-host. Dit
document beschrijft wat er feitelijk over de lijn kwam — niet wat het apparaat
volgens documentatie zou moeten doen. Er is geen fabrikantspecificatie
beschikbaar.

## Transport

| Eigenschap | Waarde |
|---|---|
| Protocol | UDP |
| Bron | `192.168.1.42`, wisselende bronpoort (`41710` tijdens de capture) |
| Bestemming | `192.168.1.255:8484` — **subnet-broadcast** |
| Interval | ~5,0 s |
| Grootte | 221 bytes |
| Encoding | UTF-8, één compleet JSON-object per datagram |

Geen framing, geen lengte-prefix, geen fragmentatie. Elk datagram staat op
zichzelf.

### Gevolgen voor de implementatie

**Binden op `0.0.0.0`, nooit op het host-IP.** Een socket die aan een specifiek
interface-adres hangt ontvangt op Linux geen subnet-broadcast. Dat faalt stil:
je krijgt nul pakketten en geen enkele foutmelding.

**`SO_REUSEADDR` en `SO_REUSEPORT` zetten.** Die tweede maakt het mogelijk om
tegelijk met de draaiende integratie mee te luisteren voor debugging, zonder
Home Assistant stil te leggen.

**De bronpoort is efemeer** en verandert per sessie. Filter op de payload
(`protocol`-veld), niet op poortnummer of afzenderadres.

## Envelope

Elk bericht begint met dezelfde velden:

| Veld | Type | Betekenis |
|---|---|---|
| `protocol` | string | Altijd `"moma"`. Magic string — verwerp alles wat niet matcht. |
| `version` | int | Protocolversie, momenteel `1`. |
| `type` | string | Berichtsoort. Tot nu toe alleen `"state"` waargenomen. |
| `name` | string | Apparaatidentiteit: `Moma` + serienummer, bv. `MomaXXXXXX`. Uniek per apparaat. Basis voor `unique_id`. |
| `sequence` | int | Monotoon oplopende teller per apparaat. |
| `timestamp` | int | Epoch in milliseconden (UTC). Komt overeen met de kloktijd van de capture. |

Deze envelope is duidelijk met opzet ontworpen en maakt drie dingen mogelijk:

- **Validatie** — `protocol` + `version` filteren vreemd verkeer op poort 8484 weg.
- **Multi-device op één poort** — omdat `name` in elk pakket zit, kan één socket
  meerdere apparaten bedienen en die automatisch als aparte devices aanmaken.
  Zie [Identiteit](#identiteit) hieronder.
- **Volgorde en verlies** — zie hieronder.

### Identiteit

`name` is opgebouwd als `Moma` + serienummer. Het serienummer is uniek per
apparaat; andere gebruikers hebben hetzelfde apparaattype met een ander nummer.
Dit is geen door de gebruiker instelbare naam maar een fabrieksidentiteit.

Gevolgen:

- `name` is bruikbaar als `unique_id`, stabiel over herstarts en IP-wisselingen.
- Serienummer hoort in `DeviceInfo.serial_number`, `Moma` in `model` en
  `Smart-E-Grid` in `manufacturer` — de moma is een product van Smart-E-Grid.
  Let op dat `model` daarmee twee rollen heeft: het is óók het voorvoegsel waar
  het serienummer achter weggehaald wordt.
- Omdat de identiteit uit de broadcast zelf komt, is de integratie
  **configuratieloos**: geen IP-adres, geen handmatige naamgeving. Apparaten
  verschijnen binnen één interval na installatie.
- Er is een installed base bij andere gebruikers. Verwacht firmwarevarianten
  met velden die in deze capture ontbreken; het datamodel mag daar niet op
  stukvallen.

### Omgaan met `sequence`

UDP levert niet in volgorde en verliest pakketten zonder melding.

- Een `sequence` **lager dan de laatst verwerkte** voor datzelfde `name` is een
  verlaat pakket en moet verworpen worden. Verwerk je het toch, dan springen
  vermogenswaarden terug in de tijd en krijg je zaagtanden in de grafieken.
- Een **gat** in de reeks is meetbaar pakketverlies. Geschikt als diagnostic
  sensor.
- Bij herstart van het apparaat springt de teller vermoedelijk terug naar 1.
  Dat is niet te onderscheiden van een extreem verlaat pakket zonder ook
  `timestamp` mee te wegen. **Nog niet geverifieerd.**

## Berichttype `state`

Voorbeeld (geanonimiseerd — `name` vervangen):

```json
{
  "protocol": "moma",
  "version": 1,
  "type": "state",
  "name": "TESTDEVICE01",
  "sequence": 1,
  "timestamp": 1785154712978,
  "grid_power_w": 0,
  "home_power_w": 0,
  "pv_power_w": 0,
  "battery_power_w": 0,
  "battery_soc": 0,
  "frequency_hz": 0,
  "online": true
}
```

| Veld | Eenheid | Voorgestelde mapping |
|---|---|---|
| `grid_power_w` | W | `device_class: power`, `state_class: measurement` |
| `home_power_w` | W | idem |
| `pv_power_w` | W | idem |
| `battery_power_w` | W | idem |
| `battery_soc` | % (0–100) | `device_class: battery`, `state_class: measurement` |
| `frequency_hz` | Hz | `device_class: frequency`, `state_class: measurement` |
| `online` | bool | **geen entiteit** — zie hieronder |

Tijdens de capture stonden **alle numerieke waarden op 0**. Het apparaat was
inactief. Dat betekent dat de mapping hierboven op veldnamen berust en nog niet
tegen echte meetwaarden gevalideerd is.

`online` krijgt bewust geen entiteit. Het veld staat op `true` in elk pakket dat
we ooit gezien hebben, dus het onderscheidt niets: een apparaat dat `false` zou
willen melden, zou dat pakket ook moeten kunnen versturen. Beschikbaarheid
bepalen we daarom aan de hand van de vraag of er nog pakketten binnenkomen
(ontwerpbeslissing 4), en niet uit een veld in de payload. Zie
`IGNORED_FIELDS` in `protocol/activation.py`.

### Eén apparaat, groeiend aantal velden

De laadpaal krijgt geen eigen `name` en geen eigen broadcast: hij levert extra
velden binnen hetzelfde `state`-bericht.

Gevolg voor het datamodel: **één Home Assistant-device per `name`**, met een
veldenlijst die over de tijd groeit.

Eén device betekent niet één sensor. Elk veld wordt een eigen entiteit onder
dat device, allemaal met dezelfde prefix:

```
Device:  MomaXXXXXX
├─ sensor.momaxxxxxx_grid_power_w
├─ sensor.momaxxxxxx_home_power_w
├─ sensor.momaxxxxxx_pv_power_w
├─ sensor.momaxxxxxx_battery_power_w
├─ sensor.momaxxxxxx_battery_soc
├─ sensor.momaxxxxxx_frequency_hz
└─ (later) sensor.momaxxxxxx_charger_power_w
```

Wat hiermee vervalt is het alternatief: de laadpaal als **eigen** device met een
`via_device`-koppeling naar de Moma, dus twee kaarten met een ouder-kindrelatie.
Dat zou nodig zijn geweest als de laadpaal een eigen `name` broadcastte. Nu
hoort alles onder één device, wat aanzienlijk eenvoudiger is.

Twee dingen bepalen welke entiteiten er werkelijk komen: `online` wordt nooit
een sensor, en een veld verschijnt pas nadat het één keer een waarde had die
niet nul is (ontwerpbeslissing 13).

Die extra velden zitten nog niet in de huidige firmware. Ze komen binnen op
`version: 1` en activeren bij hun eerste waarde die niet nul is, dus er is geen
release nodig om ze te ondersteunen.

### Het veldenoverzicht is compleet en stabiel

Een `state`-bericht bevat altijd álle velden die het apparaat kan aanbieden, ook
die van functies die niet in gebruik zijn. Velden zijn dus niet optioneel en
ontbreken niet.

Twee gevolgen:

- **Uit de aanwezigheid van een veld valt niets af te leiden.** Of een veld
  bruikbaar is, blijkt alleen uit zijn waarde — zie
  ontwerpbeslissing 13.
- **Een veldnaam die niet eerder voorkwam betekent een firmwarewijziging.**
  Omdat het schema anders stabiel is, is dat een betrouwbaar signaal. Uitbreiding
  van de firmware met extra velden is aangekondigd en zal dus gebeuren; de
  integratie moet daar zonder release op reageren.

Praktisch controlemiddel: in de inventaris van de recorder hoort elk veld een
`count` te hebben die gelijk is aan `packets`. Een lagere `count` betekent dat
het veld tijdens de opname is verschenen — of dat de aanname hierboven niet
klopt.

### `version` verandert niet mee met de velden

Bij het toevoegen van sensoren blijft `version` op `1`. Nieuwe velden komen dus
binnen op de bestaande versie en worden gewoon verwerkt.

Dat maakt de strikte versiecontrole in `messages.py` veilig én zinvol. Veilig,
omdat een firmware-uitbreiding de parser niet stillegt. Zinvol, omdat een
verhoging naar `2` dan per definitie géén extra sensoren betekent maar iets
structureels — mogelijk een gewijzigde betekenis van bestaande velden. Zulke
pakketten weigeren is dan het juiste: liever geen data dan verkeerde data in de
statistieken.

`SUPPORTED_VERSIONS` uitbreiden is een bewuste handeling, pas nadat een nieuwe
versie waargenomen en begrepen is.

## Openstaande vragen

Nog één, en die is af te lezen uit een opname in plaats van na te vragen. Hij
staat ook in [`veldnaamconventie.md`](veldnaamconventie.md), het document dat
met de ontwikkelaars van het apparaat gedeeld wordt — bij een antwoord moeten
beide bijgewerkt worden.

1. **`sequence` bij apparaatherstart** — terug naar 1 of doorlopend? Te
   observeren door het apparaat één keer bewust te herstarten terwijl de
   recorder loopt.

   *De ontwikkelaars geven aan dat de teller vrijwel zeker herstart bij 1. Nog
   niet waargenomen.* De volgordebewaking gaat daar inmiddels op beide manieren
   mee om, ook als de klok van het apparaat achteruit springt — zie
   beslissing 4.

### Vastgesteld

- **Tekenconventie van de vermogensvelden**, opgegeven door de ontwikkelaars van
  het apparaat:

  | Veld | Negatief | Positief |
  |---|---|---|
  | `grid_power_w` | injectie op het net | verbruik van het net |
  | `battery_power_w` | ontladen | laden |

  Voor de sensoren verandert dit niets: die geven de waarde weer zoals hij
  binnenkomt. Het gaat meespelen zodra er kWh-tellers uit afgeleid worden, want
  het Energy dashboard wil verbruik en injectie als aparte reeksen — en dan
  bepaalt het teken in welke van de twee een meting terechtkomt.
- **`state` is voorlopig het enige berichttype.** "Voorlopig" is hier het
  operatieve woord: de parser weigert onbekende types daarom niet, hij laat ze
  door zonder ze te interpreteren. Zo legt de recorder een nieuw type vast in
  plaats van het weg te gooien, en kan de sensorlaag zich beperken tot
  `type == "state"`.
- **Geen cumulatieve kWh-tellers.** Het apparaat stuurt uitsluitend momentane
  waarden. Zie ontwerpbeslissing 10.
- **`battery_soc` loopt van 0 tot 100** en is dus een percentage.
- **De laadpaal wordt geen apart apparaat**, maar levert extra velden in het
  bestaande `state`-bericht. Zie hieronder.
- **`version` blijft `1`** bij het toevoegen van sensoren.
- **Velden zijn niet optioneel**; het veldenoverzicht is compleet en stabiel per
  firmwareversie.

Onderstaande secties beschrijven wat we zelf al vastgesteld hebben.

**Er zijn geen kWh-tellers.** Alleen momentane vermogens. Het Home Assistant
Energy dashboard vereist `device_class: energy` met `state_class:
total_increasing` in kWh. Twee routes: een Riemann-sum helper over de
watt-sensoren leggen (werkt, maar met een broadcast om de 5 s en pakketverlies
loopt dat weg), of hopen dat het apparaat totalen in een ander berichttype
stuurt. Zolang we alleen `state` gezien hebben, is dit onbeslist.

**De tekenconventie is bekend** — zie [Vastgesteld](#vastgesteld) hierboven.
Negatief is injectie op het net en ontladen van de batterij; positief is verbruik
en laden. Dat is precies wat het Energy dashboard nodig heeft om verbruik en
injectie te scheiden, mócht er ooit een kWh-teller uit afgeleid worden.

**Welke andere `type`-waarden bestaan er?** Het veld impliceert meerdere
soorten. Alleen een langere capture — het liefst tijdens een echte laadsessie —
kan dit uitwijzen.

**Hoe verschijnt de laadpaal?** Als een tweede `name` op dezelfde broadcast, of
als extra velden binnen hetzelfde `state`-bericht? Dit bepaalt of het
device-model één apparaat met veel sensoren is, of meerdere apparaten.

**Gedrag bij herstart** van het apparaat: springt `sequence` terug naar 1?

## Capture reproduceren

Op de Home Assistant-host, via de *Advanced SSH & Web Terminal*-add-on.

> **`tcpdump` werkt daar niet**, ook niet met protection mode uit. De add-on
> krijgt `NET_ADMIN`, `SYS_ADMIN`, `SYS_RAWIO`, `SYS_TIME` en `SYS_NICE`, maar
> **geen `NET_RAW`** — en zonder die capability kan geen enkel programma een
> packet socket openen. Het commando faalt met *"You don't have permission to
> perform this capture on that device"*. Geverifieerd op HAOS 17.3 met
> add-on v24.0.1.

Een gewone UDP-socket heeft die capability niet nodig en ziet precies hetzelfde:

```sh
python3 - <<'EOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
s.bind(("0.0.0.0", 8484))
while True:
    data, addr = s.recvfrom(65535)
    print(addr, data.decode("utf-8", "replace"))
EOF
```

`SO_REUSEPORT` zorgt dat dit naast een draaiende integratie kan: bij broadcast
krijgt elke socket zijn eigen kopie, dus je snoept niets af. Voor opnemen naar
een bestand gebruik je liever de recorder, die dit al doet plus samenvatten.

Welke berichttypes zijn langsgekomen:

```sh
grep -o '"type":"[^"]*"' /share/moma/capture.log | sort | uniq -c
```
