"""Tests voor het parsen van moma-pakketten.

De payload hieronder is de echte capture van 2026-07-27, met het serienummer
vervangen. Zie docs/protocol.md.
"""

import pytest

from protocol.messages import InvalidPacket, parse_packet

STATE_PACKET = (
    b'{"protocol":"moma","version":1,"type":"state","name":"TESTDEVICE01",'
    b'"sequence":1,"timestamp":1785154712978,"grid_power_w":0,"home_power_w":0,'
    b'"pv_power_w":0,"battery_power_w":0,"battery_soc":0,"frequency_hz":0,'
    b'"online":true}'
)


def test_parses_the_envelope_of_a_state_packet():
    message = parse_packet(STATE_PACKET)

    assert message.name == "TESTDEVICE01"
    assert message.type == "state"
    assert message.version == 1
    assert message.sequence == 1
    assert message.timestamp == 1785154712978


def test_exposes_measurement_fields_separate_from_the_envelope():
    message = parse_packet(STATE_PACKET)

    assert message.fields["grid_power_w"] == 0
    assert message.fields["battery_soc"] == 0
    assert message.fields["online"] is True
    assert "protocol" not in message.fields
    assert "sequence" not in message.fields


def test_keeps_fields_it_does_not_recognise():
    # Andere gebruikers draaien andere firmware. Wat wij niet kennen mag niet
    # verdwijnen -- de recorder bestaat juist om dat op te vangen.
    message = parse_packet(
        b'{"protocol":"moma","version":1,"type":"state","name":"TESTDEVICE01",'
        b'"sequence":7,"timestamp":1785154712978,"charger_power_w":3680,'
        b'"nog_onbekend":"x"}'
    )

    assert message.fields["charger_power_w"] == 3680
    assert message.fields["nog_onbekend"] == "x"


def test_keeps_the_complete_document_for_diagnostics():
    message = parse_packet(STATE_PACKET)

    assert message.raw["protocol"] == "moma"
    assert message.raw["name"] == "TESTDEVICE01"


def test_accepts_an_unknown_message_type():
    # `type` impliceert meer soorten dan `state`; welke weten we nog niet.
    # Weigeren zou betekenen dat de recorder precies mist waarvoor hij draait.
    message = parse_packet(
        b'{"protocol":"moma","version":1,"type":"iets_nieuws","name":"TESTDEVICE01",'
        b'"sequence":2,"timestamp":1785154712978}'
    )

    assert message.type == "iets_nieuws"


def test_rejects_a_payload_that_is_not_json():
    with pytest.raises(InvalidPacket):
        parse_packet(b"\x00\x01\x02 dit is geen json")


def test_rejects_json_that_is_not_an_object():
    with pytest.raises(InvalidPacket):
        parse_packet(b"[1, 2, 3]")


def test_rejects_a_foreign_protocol_on_the_same_port():
    with pytest.raises(InvalidPacket):
        parse_packet(b'{"protocol":"iets-anders","version":1,"type":"state"}')


def test_rejects_an_unsupported_protocol_version():
    with pytest.raises(InvalidPacket):
        parse_packet(
            b'{"protocol":"moma","version":99,"type":"state","name":"TESTDEVICE01",'
            b'"sequence":1,"timestamp":1785154712978}'
        )


def test_rejects_a_packet_missing_an_envelope_field():
    with pytest.raises(InvalidPacket):
        parse_packet(
            b'{"protocol":"moma","version":1,"type":"state","sequence":1,'
            b'"timestamp":1785154712978}'
        )
