# Ontwerpbeslissingen

Genomen beslissingen met hun reden, zodat ze later niet zonder aanleiding
teruggedraaid worden. Chronologisch, nieuwste onderaan.

Status van dit document: het ontwerp is nog niet af. Wat hier staat ligt vast;
wat ontbreekt wacht op de fabrikantsdocumentatie en een langere capture.

---

## 1. Distributie via HACS, niet via core of een MQTT-bridge

Home Assistant core is voorlopig geen route: core eist dat apparaat­communicatie
in een aparte PyPI-library zit en neemt in de praktijk alleen integraties op
voor producten met een toegewijde maintainer. Een MQTT-discovery-bridge zou
breder werken (ook openHAB, Domoticz), maar vereist een broker en levert
MQTT-entities in plaats van een config flow met device-pagina — een slechtere
ervaring voor wie simpelweg zijn laadpaal in Home Assistant wil.

HACS geeft twee klikken installeren, eigen releasebeheer en geen poortwachters.

Core blijft open als latere optie, zie beslissing 2.

## 2. Twee lagen met een harde grens

Laag 1 (`custom_components/moma/protocol/`) doet transport, parsen en
validatie, en importeert **niets** uit Home Assistant. Laag 2 doet config flow,
devices, entities en availability.

De grens is er om drie redenen. Laag 1 is volledig testbaar met bytestrings,
zonder Home Assistant op te starten. Als core later alsnog in beeld komt,
publiceer je die map als PyPI-pakket en is aan de belangrijkste eis voldaan.
En een eventuele MQTT-bridge wordt dan een tweede dunne consument van dezelfde
library in plaats van een tweede implementatie die uit elkaar groeit.

Laag 1 staat fysiek *binnen* de integratiemap omdat HACS alleen
`custom_components/moma/` uitlevert. Behandel hem desondanks als een apart
pakket: eigen versienummer, eigen tests, geen HA-imports.

## 3. Binden op `0.0.0.0` met `SO_REUSEPORT`

Het verkeer is subnet-broadcast. Een socket gebonden aan het host-IP ontvangt
die niet en faalt stil — nul pakketten, geen foutmelding.

`SO_REUSEPORT` staat toe dat een debug-listener meeluistert terwijl de
integratie draait, zonder Home Assistant stil te leggen.

## 4. Volgordebewaking op `sequence`, niet op aankomsttijd

UDP levert niet in volgorde. Een pakket met een lager `sequence` dan het laatst
verwerkte voor hetzelfde apparaat wordt verworpen; anders springen
vermogenswaarden terug en ontstaan zaagtanden in de statistieken. Gaten in de
reeks zijn meetbaar pakketverlies en worden een diagnostic sensor.

Een herstart van het apparaat zet de teller terug naar 1 en is daarmee niet te
onderscheiden van een verlaat pakket. Er zijn daarom **twee uitwegen**, en beide
zijn nodig:

1. **Klok vooruit.** Is de `timestamp` juist vooruit gesprongen, dan is het een
   herstart. Dit is het normale geval.
2. **Grote terugval van de teller.** Valt de teller met minstens tien plaatsen
   terug, dan is het ook een herstart — ongeacht de klok.

Die tweede regel dekt een herstart waarbij het apparaat nog geen betrouwbare tijd
heeft: geen RTC, of NTP nog niet gesynchroniseerd. Dan springt de `timestamp`
*achteruit* en faalt regel 1. Zonder regel 2 zou de tracker elk pakket weigeren
tot de teller weer boven de oude waarde uitkomt — bij een teller op 500 en vijf
seconden per pakket veertig minuten stilte, zonder iets in het log. Precies het
soort storing dat niemand opmerkt.

De drempel van tien plaatsen scheidt de twee gevallen: UDP levert pakketten door
elkaar met een paar plaatsen verschil, nooit met honderden.

## 5. Configuratieloze discovery, `name` als identiteit

`name` is `Moma` + een uniek serienummer dat het apparaat zelf uitzendt. Dat
wordt de `unique_id`, met het serienummer in `DeviceInfo.serial_number`.

Omdat de identiteit uit de broadcast komt, hoeft de gebruiker geen IP-adres of
naam in te vullen: integratie toevoegen, poort staat voorgevuld op 8484,
apparaten verschijnen binnen één interval. Meerdere apparaten per installatie
werken zonder extra werk.

## 6. Hybride afhandeling van velden, via een declaratieve catalogus

Bekende velden krijgen een nette naam, vertaling en de juiste `device_class`.
Onbekende velden worden alleen entities als de gebruiker "experimentele velden"
aanzet.

De kennis over velden staat als **data** in een catalogus, niet als
`if`-takken in de sensorcode: per veldnaam de eenheid, `device_class`,
`state_class`, vertaalsleutel en of de waarde cumulatief of momentaan is.

Een veld toevoegen is dan één regel data in plaats van een codewijziging, de
hele lijst is in één keer te reviewen tegen de fabrikantsdocumentatie, en CI kan
afdwingen dat elke combinatie geldig is — Home Assistant weigert bijvoorbeeld
`device_class: energy` met eenheid `W`, en dat wil je in een test zien en niet
in het logbestand van een gebruiker.

Aanleiding: dit is een product met een installed base. Andere gebruikers hebben
andere varianten en firmwareversies. De strikte variant zou voor elke
firmwarevariant een release vereisen; de volledig tolerante variant levert
rommelige entity-namen zonder vertaling en maakt van elke firmware-typefout een
permanente entity in ieders installatie.

## 7. Diagnostics vanaf het begin

De integratie implementeert het `diagnostics`-platform en geeft daarin de
laatste ruwe payloads terug, met serienummer geredigeerd.

Zonder dat moet je gebruikers met afwijkende hardware door een tcpdump-sessie
praten. Met één downloadknop plakken ze het bestand in een issue. Voor een
integratie die onderhouden moet worden op hardware die de maintainer zelf niet
bezit, is dit geen luxe.

## 8. Ruwe captures blijven buiten git

`captures/` staat in `.gitignore`. Alleen handmatig geanonimiseerde monsters
gaan naar `fixtures/`.

De repo is nu privé maar wordt publiek gezet, inclusief de volledige historie.
Ruwe captures bevatten huishoudelijke telemetrie: verbruikspatronen verraden
aanwezigheid, laadsessies verraden rijgedrag, en `name` is een serienummer.
Achteraf herstellen vereist history rewriten of een verse repo.

## 9. Eerst een standalone recorder, dan pas entities

Volgorde van bouwen: eerst een recorder die op de Home Assistant-host draait en
elk pakket als JSONL wegschrijft, daarna pas het datamodel en de entities.

Het datamodel ontwerpen op de enige capture die we hebben zou betekenen dat we
het baseren op vier velden die toevallig allemaal 0 waren. Het opgebouwde
corpus wordt bovendien permanent testmateriaal: een echte laadsessie met echte
SOC-verlopen en vermogenspieken is een testcase die je zelf niet zou verzinnen.

Uitvoering in twee stappen: een script in de *Advanced SSH & Web
Terminal*-add-on voor de eerste data, daarna dezelfde code verpakt als lokale
add-on onder `/addons/` zodat hij herstarts en updates overleeft en dagenlang
op een laadsessie kan wachten. Zelf containers starten op HA OS is bewust
vermeden: dat markeert het systeem als unsupported.

## 10. Monitoren eerst, Energy dashboard later

Het apparaat stuurt uitsluitend momentane waarden; er zijn geen kWh-tellers.
Koppeling met het Energy dashboard zou dus betekenen dat de integratie zelf
integreert — en dan **twee tellers per vermogensveld**, want het dashboard wil
import en export als aparte, monotoon stijgende sensoren. Eén sensor met een
saldo werkt niet, omdat `state_class: total_increasing` niet mag dalen.

Dat valt buiten de eerste versie. Het doel is de velden als sensoren in Home
Assistant zichtbaar maken. De afgeleide kWh-tellers komen later, en zijn dan
alleen te valideren tegen een opgenomen echte laadsessie.

## 11. Entiteitsnamen volgen het veld letterlijk

`unique_id` wordt `<name>_<veld>`, dus `MomaXXXXXX_grid_power_w`. Die identiteit
komt volledig uit de broadcast en is daarmee stabiel over herinstallaties,
hernoemingen en IP-wisselingen heen.

De `entity_id` volgt diezelfde vorm: `sensor.momaxxxxxx_grid_power_w`, in
kleinletters.

Home Assistant leidt de entity_id normaal af uit de apparaatnaam plus de
weergavenaam. Dat zou het eenheidstoken laten wegvallen zodra de weergavenaam
"Grid power" is. Een entiteit mag zijn entity_id echter **zelf voorstellen** door
`self.entity_id` te zetten; `entity_platform.py` zegt dat letterlijk:

> `# An entity may suggest the entity_id by setting entity_id itself`

Daarmee zijn beide mogelijk: de weergavenaam is "Grid power" en de entity_id
blijft `sensor.momaxxxxxx_grid_power_w`. Een eerdere versie van deze beslissing
stelde dat je moest kiezen; dat was onjuist.

Waarom de entity_id het veld letterlijk volgt: dit is een monitoring-integratie.
Gebruikers schrijven er templates, automatiseringen en dashboards tegenaan, en
dan is een entity_id die exact overeenkomt met wat er in de JSON staat meer waard
dan een mooie afkorting.

Bestaat de entiteit al in het register, dan wint het register. Hernoemen door de
gebruiker blijft dus werken — met de bekende keerzijde dat het patroon dan
doorbroken wordt.

## 12. Eenheden afleiden uit het laatste naamtoken

De catalogus koppelt het laatste underscore-token van een veldnaam aan een
eenheid en `device_class`: `_w` → watt, `_hz` → hertz, `_soc` → procent,
enzovoort. `grid_power_w` levert `w`, `battery_soc` levert `soc`.

Datzelfde token bepaalt ook de weergavenaam. Een **eenheidstoken** valt weg,
want de eenheid staat al naast de waarde: `grid_power_w` wordt "Grid power". Een
**semantisch token** blijft staan, want het draagt betekenis: `battery_soc`
zonder `soc` zou "Battery" opleveren, en dat zegt niet dat het om de laadtoestand
gaat. Bij een onbekend token blijven alle woorden staan — dan weten we niet of
het laatste deel een eenheid is of betekenis.

Een veld met een onbekend token wordt gewoon een sensor, alleen zonder eenheid
en zonder `device_class`. Zo valt nieuwe firmware nooit stil op een naam die wij
niet kennen. Uitzondering is `online`: dat veld staat op de negeerlijst en krijgt
helemaal geen entiteit (zie beslissing 13).

Deze regel is de reden dat de hybride aanpak uit beslissing 6 werkt zonder
release: firmware die een nieuw veld `charger_power_w` gaat sturen, krijgt
automatisch de juiste eenheid en `device_class`.

## 13. Een veld wordt pas een sensor als het ooit een waarde had

Een `state`-bericht bevat altijd álle velden die het apparaat kán aanbieden, ook
die van functies die niet in gebruik zijn. Uit de aanwezigheid van een veld
valt dus niets af te leiden — alleen uit zijn waarde. Een veld dat permanent
nul blijft is aanwezig in het schema maar niet in gebruik, en zou een nutteloze
sensor opleveren.

Een veld activeert daarom bij zijn eerste waarde die niet nul is. `online` wordt
nooit een sensor: beschikbaarheid bepalen we aan de hand van de vraag of er nog
pakketten binnenkomen (beslissing 4), niet uit een veld in de payload.

**Activering is eenrichtingsverkeer.** Zonnepanelen staan 's nachts op nul en een
laadpaal staat het grootste deel van de tijd stil. Zou een veld deactiveren bij
een nul, dan verdwijnt de PV-sensor elke nacht en breken dashboards en
automatiseringen die ernaar verwijzen. Om dezelfde reden wordt de
activeringsstatus bewaard: na een herstart om drie uur 's nachts moeten de
sensoren er meteen weer zijn, niet pas bij zonsopgang.

Negatieve waarden activeren wél — injectie op het net is net zo goed een meting
als afname.

De inventaris van de recorder rapporteert `active_fields` per apparaat. Wat daar
na een lange opname niet in staat, bleef de hele tijd nul.

Omdat het schema stabiel is, betekent een veldnaam die niet eerder voorkwam een
firmwarewijziging. Uitbreiding met extra velden is aangekondigd. De
activeringslogica geeft per bericht terug welke velden nieuw activeren, dus een
nieuw veld levert automatisch een sensor op bij zijn eerste echte waarde — zonder
release en zonder herconfiguratie. Samen met de eenheidsregel uit beslissing 12
krijgt dat veld ook meteen de juiste `device_class`.
