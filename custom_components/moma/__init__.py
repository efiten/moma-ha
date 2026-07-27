"""De moma-integratie voor Home Assistant.

Nog niet functioneel. De transport- en protocollaag is klaar en zit in
`protocol/`; de Home Assistant-lijm -- config flow, devices, entities --
volgt zodra er een opname is van een actief apparaat. Zie
docs/ontwerpbeslissingen.md, beslissing 9.

`config_flow` staat daarom nog op `false` in manifest.json, en `iot_class` op
`local_push`: het apparaat broadcast ongevraagd, er wordt niets gepolld.
"""

DOMAIN = "moma"
