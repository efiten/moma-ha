"""Tests voor volgordebewaking op `sequence`.

UDP levert niet in volgorde en verliest pakketten. Zie
docs/ontwerpbeslissingen.md, beslissing 4.
"""

import json

from protocol.messages import parse_packet
from protocol.ordering import SequenceTracker

BASE_TIMESTAMP = 1785154712978


def message(name="TESTDEVICE01", sequence=1, timestamp=None):
    """Bouw een pakket met de gevraagde envelope-waarden."""
    if timestamp is None:
        # Vijf seconden per pakket, zoals het apparaat werkelijk verstuurt.
        timestamp = BASE_TIMESTAMP + sequence * 5000
    return parse_packet(
        json.dumps(
            {
                "protocol": "moma",
                "version": 1,
                "type": "state",
                "name": name,
                "sequence": sequence,
                "timestamp": timestamp,
                "grid_power_w": 0,
            }
        ).encode()
    )


def test_accepts_the_first_packet_from_a_device():
    tracker = SequenceTracker()

    assert tracker.accept(message(sequence=1)) is True


def test_accepts_a_higher_sequence():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=1))

    assert tracker.accept(message(sequence=2)) is True


def test_rejects_a_packet_that_arrives_late():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=5))

    assert tracker.accept(message(sequence=4)) is False


def test_rejects_a_duplicate():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=5))

    assert tracker.accept(message(sequence=5)) is False


def test_tracks_devices_independently():
    tracker = SequenceTracker()
    tracker.accept(message(name="TESTDEVICE01", sequence=100))

    assert tracker.accept(message(name="TESTDEVICE02", sequence=1)) is True


def test_accepts_a_sequence_reset_when_the_timestamp_moved_forward():
    # Herstart van het apparaat: teller terug naar 1, maar de klok loopt door.
    # Zonder deze regel zou de integratie na elke herstart stil vallen.
    tracker = SequenceTracker()
    tracker.accept(message(sequence=500, timestamp=BASE_TIMESTAMP))

    assert tracker.accept(message(sequence=1, timestamp=BASE_TIMESTAMP + 60_000)) is True


def test_accepts_a_reset_even_when_the_clock_went_backwards():
    # Het apparaat herstart de teller bij 1. Heeft het geen RTC of is NTP nog
    # niet gesynchroniseerd, dan springt de timestamp juist achteruit. Zonder
    # deze uitweg weigert de tracker elk pakket tot de teller weer boven 500
    # uitkomt -- bij vijf seconden per pakket veertig minuten stilte.
    tracker = SequenceTracker()
    tracker.accept(message(sequence=500, timestamp=BASE_TIMESTAMP))

    assert tracker.accept(message(sequence=1, timestamp=0)) is True


def test_a_genuinely_late_packet_is_still_rejected():
    # Een verlaat of dubbel bezorgd pakket scheelt een paar nummers, geen
    # honderden. Dat onderscheid houdt de bescherming tegen zaagtanden intact.
    tracker = SequenceTracker()
    tracker.accept(message(sequence=500, timestamp=BASE_TIMESTAMP))

    assert tracker.accept(message(sequence=498, timestamp=BASE_TIMESTAMP - 10_000)) is False


def test_a_clockless_reset_does_not_count_as_loss():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=500, timestamp=BASE_TIMESTAMP))
    tracker.accept(message(sequence=1, timestamp=0))

    assert tracker.lost_for("TESTDEVICE01") == 0


def test_counts_packets_lost_in_a_gap():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=1))
    tracker.accept(message(sequence=5))

    assert tracker.lost_for("TESTDEVICE01") == 3


def test_a_sequence_reset_does_not_count_as_loss():
    tracker = SequenceTracker()
    tracker.accept(message(sequence=500, timestamp=BASE_TIMESTAMP))
    tracker.accept(message(sequence=1, timestamp=BASE_TIMESTAMP + 60_000))

    assert tracker.lost_for("TESTDEVICE01") == 0
