"""Tests voor de veldcatalogus.

De catalogus koppelt het laatste underscore-token van een veldnaam aan een
eenheid, `device_class` en `state_class` (ontwerpbeslissing 12). Zo krijgt een
veld dat een firmware-update straks toevoegt automatisch de juiste behandeling.
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.sensor.const import (
    DEVICE_CLASS_STATE_CLASSES,
    DEVICE_CLASS_UNITS,
)

from custom_components.moma.fields import CATALOGUE, describe, unit_token


def test_takes_the_last_underscore_token():
    assert unit_token("grid_power_w") == "w"


def test_a_semantic_token_also_counts():
    assert unit_token("battery_soc") == "soc"


def test_a_name_without_underscore_is_its_own_token():
    assert unit_token("online") == "online"


def test_watt_becomes_a_power_sensor():
    spec = describe("grid_power_w")

    assert spec.device_class is SensorDeviceClass.POWER
    assert spec.state_class is SensorStateClass.MEASUREMENT
    assert spec.unit == "W"


def test_soc_becomes_a_battery_percentage():
    spec = describe("battery_soc")

    assert spec.device_class is SensorDeviceClass.BATTERY
    assert spec.unit == "%"


def test_hertz_becomes_a_frequency_sensor():
    spec = describe("frequency_hz")

    assert spec.device_class is SensorDeviceClass.FREQUENCY
    assert spec.unit == "Hz"


def test_kwh_becomes_a_cumulative_energy_sensor():
    # Nog niet in gebruik -- het apparaat stuurt geen tellers -- maar als de
    # firmware ze ooit toevoegt, moet de behandeling meteen kloppen.
    spec = describe("total_kwh")

    assert spec.device_class is SensorDeviceClass.ENERGY
    assert spec.state_class is SensorStateClass.TOTAL_INCREASING


def test_an_unknown_token_still_yields_a_usable_sensor():
    # Firmware-uitbreidingen mogen niet stilvallen op een onbekend token.
    spec = describe("iets_nieuws_xyz")

    assert spec.device_class is None
    assert spec.unit is None
    assert spec.state_class is SensorStateClass.MEASUREMENT


def test_every_catalogue_entry_uses_a_unit_home_assistant_accepts():
    # Dit is de reden dat de catalogus data is en geen if-takken: Home Assistant
    # weigert bijvoorbeeld device_class energy met eenheid W, en dat wil je in
    # CI zien in plaats van in het logbestand van een gebruiker.
    for token, spec in CATALOGUE.items():
        if spec.device_class is None:
            continue
        allowed = DEVICE_CLASS_UNITS.get(spec.device_class)
        if allowed is None:
            continue
        assert spec.unit in allowed, f"token {token!r}: {spec.unit!r} niet geldig"


def test_every_catalogue_entry_uses_an_accepted_state_class():
    for token, spec in CATALOGUE.items():
        if spec.device_class is None:
            continue
        allowed = DEVICE_CLASS_STATE_CLASSES.get(spec.device_class)
        if allowed is None:
            continue
        assert spec.state_class in allowed, f"token {token!r}: {spec.state_class!r} niet geldig"
