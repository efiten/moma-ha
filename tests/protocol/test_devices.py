"""Tests voor het bijhouden van toestand per apparaat.

De `DeviceTracker` zet een stroom datagrammen om in "wat is de laatste stand van
apparaat X" plus de gebeurtenissen waar de sensorlaag op moet reageren: een nieuw
apparaat, en nieuw geactiveerde velden. Hij bevat geen Home Assistant-code, zodat
deze logica zonder HA getest kan worden.
"""

import json

from protocol.activation import FieldActivation
from protocol.devices import DeviceTracker

BASE_TIMESTAMP = 1785154712978


def packet(name="TESTDEVICE01", sequence=1, timestamp=None, **fields):
    if timestamp is None:
        timestamp = BASE_TIMESTAMP + sequence * 5000
    return json.dumps(
        {
            "protocol": "moma",
            "version": 1,
            "type": "state",
            "name": name,
            "sequence": sequence,
            "timestamp": timestamp,
            **fields,
        }
    ).encode()


def test_a_first_packet_announces_a_new_device():
    tracker = DeviceTracker()

    update = tracker.handle(packet(grid_power_w=100))

    assert update.device == "TESTDEVICE01"
    assert update.is_new_device is True


def test_a_later_packet_from_the_same_device_is_not_new():
    tracker = DeviceTracker()
    tracker.handle(packet(sequence=1, grid_power_w=100))

    update = tracker.handle(packet(sequence=2, grid_power_w=200))

    assert update.is_new_device is False


def test_keeps_the_latest_values():
    tracker = DeviceTracker()
    tracker.handle(packet(sequence=1, grid_power_w=100))
    tracker.handle(packet(sequence=2, grid_power_w=200))

    assert tracker.values_for("TESTDEVICE01")["grid_power_w"] == 200


def test_ignores_a_payload_that_is_not_moma():
    tracker = DeviceTracker()

    assert tracker.handle(b"rommel") is None


def test_ignores_a_late_packet():
    # Anders springen vermogenswaarden terug in de tijd.
    tracker = DeviceTracker()
    tracker.handle(packet(sequence=2, grid_power_w=200))

    assert tracker.handle(packet(sequence=1, grid_power_w=100)) is None


def test_the_latest_values_survive_a_late_packet():
    tracker = DeviceTracker()
    tracker.handle(packet(sequence=2, grid_power_w=200))
    tracker.handle(packet(sequence=1, timestamp=BASE_TIMESTAMP, grid_power_w=999))

    assert tracker.values_for("TESTDEVICE01")["grid_power_w"] == 200


def test_reports_newly_activated_fields():
    tracker = DeviceTracker()

    update = tracker.handle(packet(grid_power_w=100, battery_soc=0))

    assert update.activated_fields == ("grid_power_w",)


def test_tracks_two_devices_separately():
    tracker = DeviceTracker()
    tracker.handle(packet(name="TESTDEVICE01", grid_power_w=100))
    tracker.handle(packet(name="TESTDEVICE02", grid_power_w=700))

    assert sorted(tracker.devices) == ["TESTDEVICE01", "TESTDEVICE02"]
    assert tracker.values_for("TESTDEVICE02")["grid_power_w"] == 700


def test_showing_all_fields_activates_values_that_are_zero():
    tracker = DeviceTracker(show_all_fields=True)

    update = tracker.handle(packet(grid_power_w=0, battery_soc=0))

    assert sorted(update.activated_fields) == ["battery_soc", "grid_power_w"]


def test_activation_state_can_be_restored():
    tracker = DeviceTracker()
    tracker.handle(packet(pv_power_w=1200))

    restored = DeviceTracker(activation=FieldActivation(active=tracker.activation_state()))
    update = restored.handle(packet(sequence=2, pv_power_w=800))

    assert update.activated_fields == ()


def test_values_for_an_unknown_device_is_empty():
    tracker = DeviceTracker()

    assert tracker.values_for("BESTAATNIET") == {}
