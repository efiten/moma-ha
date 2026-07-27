"""Tests voor het opnemen en terugspelen van pakketten.

Het corpus dat hiermee ontstaat is permanent testmateriaal: een echte
laadsessie levert randgevallen die je zelf niet verzint. Byte-getrouwheid is
daarom een harde eis.
"""

from protocol.recorder import JsonlRecorder, replay

PAYLOAD = (
    b'{"protocol":"moma","version":1,"type":"state","name":"TESTDEVICE01",'
    b'"sequence":1,"timestamp":1785154712978,"grid_power_w":0}'
)


def test_writes_one_line_per_packet(tmp_path):
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="192.168.1.42:41710", received_at=1.0)
        recorder.record(PAYLOAD, source="192.168.1.42:41710", received_at=6.0)

    assert len(path.read_text().splitlines()) == 2


def test_flushes_immediately_so_a_crash_loses_nothing(tmp_path):
    # De recorder draait dagenlang onbewaakt. Buffering die pas bij het sluiten
    # wegschrijft zou precies de laatste -- interessantste -- pakketten kosten.
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="192.168.1.42:41710", received_at=1.0)

        assert path.read_text().splitlines() != []


def test_appends_to_an_existing_capture(tmp_path):
    # Een herstart van de add-on mag het corpus niet wissen.
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="a", received_at=1.0)
    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="a", received_at=2.0)

    assert len(path.read_text().splitlines()) == 2


def test_replay_returns_the_payload_byte_for_byte(tmp_path):
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="192.168.1.42:41710", received_at=1.0)

    (packet,) = list(replay(path))

    assert packet.payload == PAYLOAD
    assert packet.source == "192.168.1.42:41710"
    assert packet.received_at == 1.0


def test_survives_a_payload_that_is_not_valid_utf8(tmp_path):
    # De recorder mag niet filteren op wat wij nu begrijpen.
    path = tmp_path / "capture.jsonl"
    binary = b"\xff\xfe\x00 rommel"

    with JsonlRecorder(path) as recorder:
        recorder.record(binary, source="a", received_at=1.0)

    (packet,) = list(replay(path))

    assert packet.payload == binary


def test_replay_preserves_order(tmp_path):
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        for sequence in range(5):
            recorder.record(
                PAYLOAD.replace(b'"sequence":1', f'"sequence":{sequence}'.encode()),
                source="a",
                received_at=float(sequence),
            )

    assert [packet.received_at for packet in replay(path)] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_a_readable_capture_keeps_the_json_legible(tmp_path):
    # Je moet een capture kunnen openen en gewoon kunnen lezen wat er staat,
    # zonder decoderingsstap.
    path = tmp_path / "capture.jsonl"

    with JsonlRecorder(path) as recorder:
        recorder.record(PAYLOAD, source="a", received_at=1.0)

    assert "grid_power_w" in path.read_text()
