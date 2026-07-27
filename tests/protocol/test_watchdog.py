"""Tests voor stilstandsdetectie.

De recorder draait dagenlang onbewaakt. Valt de stroom pakketten stil, dan
crasht er niets -- het proces blijft draaien en Supervisor herstart niets. Zonder
detectie ontdek je dat pas als je een opname opent die na een uur ophield.

De klok komt van buiten, zodat deze tests niet hoeven te wachten.
"""

from protocol.watchdog import StallDetector


def test_is_not_stalled_immediately_after_starting():
    detector = StallDetector(timeout=60, now=1000.0)

    assert detector.is_stalled(now=1000.0) is False


def test_is_not_stalled_before_the_timeout_passes():
    detector = StallDetector(timeout=60, now=1000.0)

    assert detector.is_stalled(now=1059.0) is False


def test_is_stalled_once_the_timeout_passes_without_packets():
    detector = StallDetector(timeout=60, now=1000.0)

    assert detector.is_stalled(now=1061.0) is True


def test_a_packet_clears_the_stall():
    detector = StallDetector(timeout=60, now=1000.0)
    detector.packet_received(now=1100.0)

    assert detector.is_stalled(now=1150.0) is False


def test_reports_how_long_the_stream_has_been_quiet():
    detector = StallDetector(timeout=60, now=1000.0)
    detector.packet_received(now=1100.0)

    assert detector.quiet_for(now=1130.0) == 30.0


def test_stalls_again_after_recovering():
    # Een apparaat dat kort wegvalt en terugkomt moet daarna opnieuw gedetecteerd
    # kunnen worden -- niet eenmalig afgaan en dan zwijgen.
    detector = StallDetector(timeout=60, now=1000.0)
    detector.packet_received(now=1100.0)

    assert detector.is_stalled(now=1161.0) is True


def test_a_timeout_of_zero_disables_detection():
    detector = StallDetector(timeout=0, now=1000.0)

    assert detector.is_stalled(now=999_999.0) is False
