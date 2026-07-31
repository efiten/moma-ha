"""Tests voor het sensorplatform.

Twee dingen staan hier centraal: entiteiten ontstaan pas wanneer een veld
activeert (ontwerpbeslissing 13), en de naamgeving volgt het protocolveld
letterlijk (ontwerpbeslissing 11).
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.moma.const import DOMAIN

from .conftest import feed, make_packet, setup_moma


async def test_a_field_with_a_value_becomes_a_sensor(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=2300))

    assert hass.states.get("sensor.testdevice01_grid_power_w").state == "2300"


async def test_a_field_that_is_zero_does_not_become_a_sensor(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=2300, battery_soc=0))

    assert hass.states.get("sensor.testdevice01_battery_soc") is None


async def test_online_never_becomes_a_sensor(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=1, online=True))

    assert hass.states.get("sensor.testdevice01_online") is None


async def test_the_sensor_follows_later_values(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(sequence=1, grid_power_w=2300))

    await feed(hass, entry, make_packet(sequence=2, grid_power_w=-500))

    assert hass.states.get("sensor.testdevice01_grid_power_w").state == "-500"


async def test_a_sensor_stays_when_its_value_returns_to_zero(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(sequence=1, pv_power_w=1200))

    await feed(hass, entry, make_packet(sequence=2, pv_power_w=0))

    assert hass.states.get("sensor.testdevice01_pv_power_w").state == "0"


async def test_the_catalogue_decides_unit_and_device_class(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=2300))

    state = hass.states.get("sensor.testdevice01_grid_power_w")
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "W"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.POWER


async def test_soc_becomes_a_battery_percentage(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(battery_soc=42))

    state = hass.states.get("sensor.testdevice01_battery_soc")
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.BATTERY


async def test_an_unknown_field_still_becomes_a_sensor(hass, free_port):
    # Firmware-uitbreidingen mogen geen release vereisen.
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(charger_power_w=3680, iets_nieuws=7))

    assert hass.states.get("sensor.testdevice01_charger_power_w").state == "3680"
    assert hass.states.get("sensor.testdevice01_iets_nieuws").state == "7"


async def test_the_display_name_is_readable(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=2300))

    state = hass.states.get("sensor.testdevice01_grid_power_w")
    assert state.attributes["friendly_name"] == "TESTDEVICE01 Grid power"


async def test_the_entity_id_follows_the_field_even_with_a_nicer_name(hass, free_port):
    # Home Assistant leidt de entity_id normaal af uit de weergavenaam, wat
    # `sensor.testdevice01_battery_soc` zou maken van "Battery SOC". Daarom zet
    # de entiteit zijn entity_id expliciet.
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(battery_soc=42))

    state = hass.states.get("sensor.testdevice01_battery_soc")
    assert state is not None
    assert state.attributes["friendly_name"] == "TESTDEVICE01 Battery SOC"


async def test_an_unknown_field_gets_a_readable_name_too(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(charger_power_w=3680))

    state = hass.states.get("sensor.testdevice01_charger_power_w")
    assert state.attributes["friendly_name"] == "TESTDEVICE01 Charger power"


async def test_unique_id_combines_device_and_field(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(grid_power_w=2300))

    registry = er.async_get(hass)
    entity = registry.async_get("sensor.testdevice01_grid_power_w")

    assert entity.unique_id == "TESTDEVICE01_grid_power_w"


async def test_the_device_carries_its_serial_number(hass, free_port):
    entry = await setup_moma(hass, free_port)
    await feed(hass, entry, make_packet(name="Moma005000", grid_power_w=1))

    devices = dr.async_get(hass)
    device = devices.async_get_device(identifiers={(DOMAIN, "Moma005000")})

    assert device is not None
    assert device.serial_number == "005000"
    assert device.manufacturer == "Smart-E-Grid"


async def test_two_devices_get_their_own_prefix(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(name="TESTDEVICE01", grid_power_w=100))
    await feed(hass, entry, make_packet(name="TESTDEVICE02", grid_power_w=700))

    assert hass.states.get("sensor.testdevice01_grid_power_w").state == "100"
    assert hass.states.get("sensor.testdevice02_grid_power_w").state == "700"


async def test_showing_all_fields_creates_sensors_for_zeroes(hass, free_port):
    entry = await setup_moma(hass, free_port, show_all_fields=True)

    await feed(hass, entry, make_packet(grid_power_w=0, battery_soc=0))

    assert hass.states.get("sensor.testdevice01_grid_power_w").state == "0"
    assert hass.states.get("sensor.testdevice01_battery_soc").state == "0"


async def test_a_power_sensor_is_a_measurement(hass, free_port):
    entry = await setup_moma(hass, free_port)

    await feed(hass, entry, make_packet(grid_power_w=2300))

    state = hass.states.get("sensor.testdevice01_grid_power_w")
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
