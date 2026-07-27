"""Tests voor de protocolinventaris.

Het doel van dagenlang opnemen is uitvinden wat het apparaat stuurt. Deze
inventaris beantwoordt dat in één oogopslag, zonder duizenden regels JSONL
door te spitten.
"""

import json

from protocol.messages import parse_packet
from protocol.survey import ProtocolSurvey


def message(name="TESTDEVICE01", type="state", sequence=1, **fields):
    return parse_packet(
        json.dumps(
            {
                "protocol": "moma",
                "version": 1,
                "type": type,
                "name": name,
                "sequence": sequence,
                "timestamp": 1785154712978 + sequence * 5000,
                **fields,
            }
        ).encode()
    )


def test_counts_the_packets_it_saw():
    survey = ProtocolSurvey()
    survey.observe(message(sequence=1))
    survey.observe(message(sequence=2))

    assert survey.summary()["packets"] == 2


def test_lists_every_device_it_saw():
    survey = ProtocolSurvey()
    survey.observe(message(name="TESTDEVICE01"))
    survey.observe(message(name="TESTDEVICE02"))

    assert sorted(survey.summary()["devices"]) == ["TESTDEVICE01", "TESTDEVICE02"]


def test_lists_every_message_type_it_saw():
    survey = ProtocolSurvey()
    survey.observe(message(type="state"))
    survey.observe(message(type="meter"))

    assert sorted(survey.summary()["types"]) == ["meter", "state"]


def test_lists_fields_per_message_type():
    # Een `meter`-bericht heeft andere velden dan een `state`-bericht. Ze op
    # één hoop gooien zou dat verschil verbergen.
    survey = ProtocolSurvey()
    survey.observe(message(type="state", grid_power_w=100))
    survey.observe(message(type="meter", total_kwh=42))

    fields = survey.summary()["fields"]

    assert "grid_power_w" in fields["state"]
    assert "total_kwh" in fields["meter"]
    assert "total_kwh" not in fields["state"]


def test_records_the_range_of_a_numeric_field():
    # Zonder bereik weet je niet of `battery_soc` 0-100 of 0-1 is, en of een
    # vermogensveld ooit negatief wordt -- de tekenconventie.
    survey = ProtocolSurvey()
    survey.observe(message(sequence=1, grid_power_w=-500))
    survey.observe(message(sequence=2, grid_power_w=2300))

    observed = survey.summary()["fields"]["state"]["grid_power_w"]

    assert observed["min"] == -500
    assert observed["max"] == 2300


def test_records_an_example_for_a_non_numeric_field():
    survey = ProtocolSurvey()
    survey.observe(message(online=True))

    observed = survey.summary()["fields"]["state"]["online"]

    assert observed["example"] is True


def test_notes_when_a_field_is_not_present_in_every_packet():
    # Optionele velden zijn belangrijk: een variant zonder batterij stuurt
    # `battery_soc` mogelijk helemaal niet.
    survey = ProtocolSurvey()
    survey.observe(message(sequence=1, grid_power_w=1, battery_soc=50))
    survey.observe(message(sequence=2, grid_power_w=1))

    fields = survey.summary()["fields"]["state"]

    assert fields["grid_power_w"]["count"] == 2
    assert fields["battery_soc"]["count"] == 1
