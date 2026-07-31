# Brand-afbeeldingen

Home Assistant haalt het logo van een integratie **niet** uit de integratie
zelf. Alle merkafbeeldingen staan in een aparte repository,
[`home-assistant/brands`](https://github.com/home-assistant/brands), en worden
uitgeleverd via `brands.home-assistant.io`. Zolang `moma` daar niet in staat,
toont Home Assistant een grijs vakje met *icon not available* — ook als er een
PNG in `custom_components/moma/` ligt.

Deze map bevat de afbeeldingen die daarvoor ingediend moeten worden. Ze staan
hier zodat ze reproduceerbaar zijn en niet uit een chatgeschiedenis
teruggevist hoeven te worden; ze doen in deze repo verder niets.

## Wat er ligt

| Bestand | Formaat | Rol |
|---|---|---|
| `custom_integrations/moma/icon.png` | 256×256 | **Vereist.** Het netwerksymbool, vierkant |
| `custom_integrations/moma/icon@2x.png` | 512×512 | hDPI-variant van het icoon |
| `custom_integrations/moma/logo.png` | 256×177 | Optioneel. Volledige merknaam |
| `custom_integrations/moma/logo@2x.png` | 512×354 | hDPI-variant van het logo |

Alle vier hebben een doorzichtige achtergrond. Het witte middelpunt van het
netwerksymbool is bewust **niet** doorzichtig gemaakt: dat is een gevulde ring in
het merkteken, geen achtergrond, en doorzichtig maken slaat er een gat in dat op
een donker thema opvalt.

## Alleen het icoon indienen

Overweeg om `logo.png` weg te laten. De merknaam staat in zwarte letters, en op
een donker thema verdwijnt die. Het icoon is enkel het rode symbool en leest op
beide thema's. Home Assistant valt zonder logo netjes terug op het icoon.

## Indienen

1. Fork `home-assistant/brands`.
2. Zet de bestanden in `custom_integrations/moma/` — het mapnaam moet exact het
   `domain` uit `custom_components/moma/manifest.json` zijn.
3. Open een pull request. De CI daar controleert formaat, vierkantheid en of de
   afbeeldingen geoptimaliseerd zijn.

Na het samenvoegen verschijnt het icoon zonder dat er iets aan deze integratie
of aan een installatie verandert; Home Assistant haalt het van de CDN.
