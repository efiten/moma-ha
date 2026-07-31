"""Constanten voor de moma-integratie."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "moma"

DEFAULT_PORT = 8484

CONF_SHOW_ALL_FIELDS = "show_all_fields"

PLATFORMS: list[Platform] = [Platform.SENSOR]

MANUFACTURER = "Smart-E-Grid"

# Het model is óók het voorvoegsel van de apparaatnaam: `Moma001539` levert
# serienummer `001539`. Wijzig dit dus niet los van `device.py`, want daar wordt
# het serienummer eruit gehaald met `removeprefix(MODEL)`.
MODEL = "Moma"

# Na zoveel seconden zonder pakket gelden de entiteiten als niet beschikbaar.
# Bij een interval van vijf seconden zijn dat twaalf gemiste pakketten, dus
# gewoon verlies levert geen valse meldingen op.
STALL_TIMEOUT = 60.0

# Hoe vaak gecontroleerd wordt of de stroom stilgevallen is. UDP meldt dat niet,
# dus zonder deze controle blijven entiteiten hun laatste waarde tonen alsof er
# niets aan de hand is.
STALL_CHECK_INTERVAL = 15.0

# Ruwe payloads voor diagnostics. Begrensd, want bij een broadcast om de vijf
# seconden zou onbegrensd bewaren geheugen blijven opeten.
MAX_DIAGNOSTIC_PAYLOADS = 20

# Melding voor het geval dat de integratie werkt maar er niets te zien is: alle
# velden staan op nul, dus er activeert er geen een en er komt zelfs geen device.
ISSUE_ALL_FIELDS_ZERO = "all_fields_zero"

SIGNAL_NEW_FIELDS = f"{DOMAIN}_new_fields"
SIGNAL_DEVICE_UPDATE = f"{DOMAIN}_device_update"

STORAGE_VERSION = 1
