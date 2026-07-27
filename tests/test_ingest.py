"""Tests voor de gedeelde verwerkingsstap.

Live meeluisteren en een opname terugspelen moeten tot exact dezelfde
inventaris leiden. Toen dat twee losse implementaties waren, telde het
terugspelen verlate pakketten wel mee en het live pad niet -- met een
vertekend bereik per veld als gevolg.
"""

import json

from protocol.ingest import Outcome, PacketIngest

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


def test_accepts_a_valid_packet():
    ingest = PacketIngest()

    assert ingest.handle(packet(sequence=1)).outcome is Outcome.ACCEPTED


def test_reports_the_parsed_message_for_an_accepted_packet():
    ingest = PacketIngest()

    result = ingest.handle(packet(sequence=1, grid_power_w=230))

    assert result.message.fields["grid_power_w"] == 230


def test_rejects_something_that_is_not_a_moma_packet():
    ingest = PacketIngest()

    assert ingest.handle(b"rommel").outcome is Outcome.REJECTED


def test_marks_a_late_packet_as_stale():
    ingest = PacketIngest()
    ingest.handle(packet(sequence=2))

    assert ingest.handle(packet(sequence=1)).outcome is Outcome.STALE


def test_a_late_packet_does_not_reach_the_survey():
    # Dit is de fout die het samenvatten van een opname eerder maakte: een
    # achterhaalde waarde verbreedde het waargenomen bereik van een veld.
    ingest = PacketIngest()
    ingest.handle(packet(sequence=1, grid_power_w=100))
    ingest.handle(packet(sequence=2, grid_power_w=200))
    ingest.handle(packet(sequence=1, timestamp=BASE_TIMESTAMP, grid_power_w=9999))

    observed = ingest.summary()["fields"]["state"]["grid_power_w"]

    assert observed["max"] == 200
    assert observed["count"] == 2


def test_counts_each_outcome():
    ingest = PacketIngest()
    ingest.handle(packet(sequence=1))
    ingest.handle(packet(sequence=2))
    ingest.handle(packet(sequence=1))
    ingest.handle(b"rommel")

    summary = ingest.summary()

    assert summary["packets"] == 2
    assert summary["stale_packets"] == 1
    assert summary["rejected_packets"] == 1


def test_reports_which_fields_would_become_sensors():
    # Na een lange opname wil je in één blik zien welke velden echt in gebruik
    # zijn, zonder duizenden regels JSONL door te spitten.
    ingest = PacketIngest()
    ingest.handle(packet(sequence=1, grid_power_w=2300, battery_soc=0))

    assert ingest.summary()["active_fields"] == {"TESTDEVICE01": ["grid_power_w"]}


def test_a_field_that_stayed_zero_is_not_reported_as_active():
    ingest = PacketIngest()
    ingest.handle(packet(sequence=1, battery_soc=0))
    ingest.handle(packet(sequence=2, battery_soc=0))

    assert ingest.summary()["active_fields"] == {}


def test_reports_lost_packets_per_device():
    ingest = PacketIngest()
    ingest.handle(packet(sequence=1))
    ingest.handle(packet(sequence=5))

    assert ingest.summary()["lost_packets"] == {"TESTDEVICE01": 3}
