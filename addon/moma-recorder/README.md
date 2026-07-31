# Moma Recorder (lokale add-on)

Neemt moma UDP-broadcasts op als JSONL. Bedoeld om dagenlang onbewaakt te
draaien terwijl je op een echte laadsessie wacht.

Dit is **geen** Supervisor-add-onrepository en hoort niet in HACS. Het is een
ontwikkelharnas dat je met de hand op de Home Assistant-machine zet.

## Waarom een add-on en niet een script in de SSH-terminal

Een script in de *Advanced SSH & Web Terminal*-add-on is dood na de eerste
herstart of update van die add-on, en alles wat je daar met `apk add`
bijgeïnstalleerd hebt is dan ook weg. Als lokale add-on beheert Supervisor het
proces: starten bij boot, herstarten na een crash, logs in de Home
Assistant-UI.

Zelf een container starten met `docker run` zou ook werken, maar markeert je
Home Assistant OS-installatie als *unsupported*.

## Installeren

Op je werkstation, in de repo:

```sh
python tools/sync_addon.py
```

Docker kan tijdens een build niet buiten zijn context kijken, dus dit zet een
kopie van de protocollaag en de CLI in deze map. Die kopieën staan in
`.gitignore`; de bron blijft `custom_components/moma/`.

Kopieer daarna de hele map `moma-recorder` naar `/addons/` op de Home
Assistant-machine. Dat kan via de Samba-add-on (netwerkschijf in Verkenner) of
met `scp` naar de SSH-add-on.

In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Check for
updates**. *Moma Recorder* verschijnt onder **Local add-ons**. Installeren,
starten, en **Start on boot** aanzetten.

## Opties

| Optie | Standaard | Betekenis |
|---|---|---|
| `port` | `8484` | UDP-poort om op te luisteren |
| `output` | `/share/moma/capture.jsonl` | Pad voor de opname; bestaande opnames worden aangevuld, niet overschreven |
| `report_every` | `3600` | Interval in seconden voor een inventaris in het log; `0` zet dit uit |
| `stall_timeout` | `60` | Waarschuwen na zoveel seconden zonder pakket; `0` zet dit uit |

De recorder logt bewust niet elk pakket: bij één broadcast per vijf seconden
zijn dat 17.000 regels per dag. De periodieke inventaris vat hetzelfde samen.

`stall_timeout` dekt het enige stille faalscenario af. Valt de stroom pakketten
weg, dan crasht er niets — het proces blijft draaien, Supervisor herstart niets,
en zonder waarschuwing merk je het pas als je een opname opent die na een uur
ophield. Bij 60 seconden zijn dat ongeveer twaalf gemiste intervallen, dus
gewoon pakketverlies veroorzaakt geen valse meldingen. Herstel wordt ook
gelogd.

## Wat er in de opname staat

Eén JSON-object per regel, met de payload als leesbare tekst onder `raw` (of
hexadecimaal onder `hex` als het geen geldige UTF-8 is). Een opname is dus met
een gewone editor te lezen zonder dat byte-getrouwheid verloren gaat.

De recorder **filtert niet** op wat de integratie begrijpt. Onbekende velden en
onbekende berichttypes worden gewoon vastgelegd — dat is juist waarvoor hij
draait.

## Een opname samenvatten

```sh
python tools/moma_record.py summary /share/moma/capture.jsonl
```

Toont welke apparaten, berichttypes en velden voorkwamen, met per numeriek veld
het waargenomen bereik. Dat bereik beantwoordt twee vragen die je anders moet
gokken: de schaal van een veld (is `battery_soc` 0–100 of 0–1?) en zijn
tekenconventie (wordt `grid_power_w` ooit negatief?).

## Privacy

Een opname bevat huishoudelijke telemetrie: verbruikspatronen verraden
aanwezigheid, laadsessies verraden rijgedrag, en `name` is een serienummer.
Opnames horen niet in git — zie de hoofd-README.
