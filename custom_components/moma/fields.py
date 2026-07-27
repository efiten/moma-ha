"""De veldcatalogus: van veldnaam naar sensoreigenschappen.

Het laatste underscore-token van een veldnaam bepaalt de eenheid en de
`device_class` (ontwerpbeslissing 12). `grid_power_w` levert `w`,
`battery_soc` levert `soc`.

Dit is bewust **data en geen if-takken**. Een veld toevoegen is één regel, de
hele lijst is in één keer te reviewen, en de tests houden elke combinatie tegen
Home Assistants eigen validatietabellen aan. Home Assistant weigert bijvoorbeeld
`device_class: energy` met eenheid `W`; die fout wil je in CI zien en niet in het
logbestand van een gebruiker.

Het apparaat kondigde aan in de toekomst extra velden te gaan sturen. Zolang die
op een bekend token eindigen, werken ze zonder release.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)


@dataclass(frozen=True)
class FieldSpec:
    """Hoe een veld als sensor gepresenteerd wordt."""

    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


CATALOGUE: dict[str, FieldSpec] = {
    # Momentane waarden -- dit is alles wat het apparaat vandaag stuurt.
    "w": FieldSpec(UnitOfPower.WATT, SensorDeviceClass.POWER),
    "kw": FieldSpec(UnitOfPower.KILO_WATT, SensorDeviceClass.POWER),
    "v": FieldSpec(UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    "a": FieldSpec(UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT),
    "hz": FieldSpec(UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY),
    "soc": FieldSpec(PERCENTAGE, SensorDeviceClass.BATTERY),
    "c": FieldSpec(UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    # Percentages zonder batterijbetekenis: eenheid wel, device_class niet.
    "pct": FieldSpec(PERCENTAGE),
    "percent": FieldSpec(PERCENTAGE),
    # Cumulatieve tellers. Het apparaat stuurt deze niet (ontwerpbeslissing 10),
    # maar als de firmware ze toevoegt moet de behandeling meteen kloppen:
    # `total_increasing` in plaats van `measurement`, anders staan de
    # langetermijnstatistieken verkeerd vanaf het eerste pakket.
    "wh": FieldSpec(
        UnitOfEnergy.WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ),
    "kwh": FieldSpec(
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ),
}

# Een onbekend token levert nog steeds een bruikbare sensor op: geen eenheid,
# geen device_class, maar wel meetwaarden met historie. Een firmware-uitbreiding
# mag nooit stilvallen omdat wij een naam niet kennen.
UNKNOWN_FIELD = FieldSpec()


def unit_token(field_name: str) -> str:
    """Het laatste underscore-token van een veldnaam.

    Let op de keerzijde van deze regel: een veld dat toevallig op een bekend
    token eindigt, krijgt die betekenis. Een hypothetisch `phase_a` zou als
    ampère gelezen worden. Dat risico is bewust genomen -- het alternatief is
    een release per nieuw veld.
    """
    return field_name.rsplit("_", 1)[-1].lower()


def describe(field_name: str) -> FieldSpec:
    """Zoek de sensoreigenschappen voor een veldnaam."""
    return CATALOGUE.get(unit_token(field_name), UNKNOWN_FIELD)
