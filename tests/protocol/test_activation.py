"""Tests voor het activeren van velden.

Het apparaat stuurt alle velden, ook die van hardware die er niet is. Een veld
dat altijd nul blijft hoort geen sensor te worden. Zie
docs/ontwerpbeslissingen.md, beslissing 13.
"""

import json

from protocol.activation import FieldActivation
from protocol.messages import parse_packet

BASE_TIMESTAMP = 1785154712978


def message(name="TESTDEVICE01", sequence=1, **fields):
    return parse_packet(
        json.dumps(
            {
                "protocol": "moma",
                "version": 1,
                "type": "state",
                "name": name,
                "sequence": sequence,
                "timestamp": BASE_TIMESTAMP + sequence * 5000,
                **fields,
            }
        ).encode()
    )


def test_a_field_that_is_zero_does_not_activate():
    activation = FieldActivation()

    assert activation.observe(message(grid_power_w=0)) == []


def test_a_field_activates_on_its_first_real_value():
    activation = FieldActivation()

    assert activation.observe(message(grid_power_w=2300)) == ["grid_power_w"]


def test_a_negative_value_also_activates():
    # Injectie op het net is net zo goed een meting als afname.
    activation = FieldActivation()

    assert activation.observe(message(grid_power_w=-500)) == ["grid_power_w"]


def test_online_is_never_activated():
    activation = FieldActivation()

    assert activation.observe(message(online=True)) == []


def test_a_field_stays_active_when_it_returns_to_zero():
    # Zonnepanelen staan 's nachts op nul. De sensor mag dan niet verdwijnen.
    activation = FieldActivation()
    activation.observe(message(sequence=1, pv_power_w=1200))
    activation.observe(message(sequence=2, pv_power_w=0))

    assert activation.is_active("TESTDEVICE01", "pv_power_w") is True


def test_a_field_is_only_reported_the_first_time():
    activation = FieldActivation()
    activation.observe(message(sequence=1, grid_power_w=100))

    assert activation.observe(message(sequence=2, grid_power_w=200)) == []


def test_activation_is_tracked_per_device():
    # De ene gebruiker heeft een batterij, de andere niet.
    activation = FieldActivation()
    activation.observe(message(name="TESTDEVICE01", battery_soc=42))

    assert activation.is_active("TESTDEVICE02", "battery_soc") is False


def test_reports_several_newly_activated_fields_at_once():
    activation = FieldActivation()

    activated = activation.observe(message(grid_power_w=100, battery_soc=0, pv_power_w=50))

    assert sorted(activated) == ["grid_power_w", "pv_power_w"]


def test_activation_survives_a_restart():
    # Zonder dit zou Home Assistant na een herstart 's nachts de PV-sensor
    # kwijt zijn tot zonsopgang.
    activation = FieldActivation()
    activation.observe(message(pv_power_w=1200))

    restored = FieldActivation(active=activation.state())

    assert restored.is_active("TESTDEVICE01", "pv_power_w") is True


def test_a_restored_field_is_not_reported_as_new_again():
    activation = FieldActivation()
    activation.observe(message(sequence=1, pv_power_w=1200))

    restored = FieldActivation(active=activation.state())

    assert restored.observe(message(sequence=2, pv_power_w=800)) == []


def test_can_activate_every_field_regardless_of_value():
    # Nodig voor een testinstallatie: bij een inactief apparaat staat alles op
    # nul, activeert er niets, en krijg je een device zonder sensoren. Dat lijkt
    # kapot terwijl het correct is.
    activation = FieldActivation(require_value=False)

    activated = activation.observe(message(grid_power_w=0, battery_soc=0))

    assert sorted(activated) == ["battery_soc", "grid_power_w"]


def test_ignored_fields_stay_ignored_even_when_value_is_not_required():
    activation = FieldActivation(require_value=False)

    assert activation.observe(message(online=True)) == []


def test_ignored_fields_can_be_configured():
    activation = FieldActivation(ignored={"grid_power_w"})

    assert activation.observe(message(grid_power_w=2300)) == []


def test_forgetting_a_device_drops_its_fields():
    # Nodig om een apparaat uit Home Assistant te kunnen verwijderen: blijft de
    # activeringsstatus staan, dan komen de sensoren bij het eerstvolgende
    # pakket meteen terug en lijkt de verwijderknop stuk.
    activation = FieldActivation()
    activation.observe(message(name="Moma005000", grid_power_w=2300))

    activation.forget("Moma005000")

    assert activation.state() == {}


def test_forgetting_leaves_other_devices_alone():
    activation = FieldActivation()
    activation.observe(message(name="Moma005000", grid_power_w=2300))
    activation.observe(message(name="Moma005001", battery_soc=72))

    activation.forget("Moma005000")

    assert sorted(activation.state()) == ["Moma005001"]


def test_forgetting_an_unknown_device_is_harmless():
    # De aanroeper weet niet zeker of dit apparaat ooit een veld activeerde.
    activation = FieldActivation()

    activation.forget("Moma005000")

    assert activation.state() == {}


def test_a_forgotten_device_can_activate_again():
    activation = FieldActivation()
    activation.observe(message(name="Moma005000", grid_power_w=2300))
    activation.forget("Moma005000")

    opnieuw = activation.observe(message(name="Moma005000", grid_power_w=2300))

    assert opnieuw == ["grid_power_w"]
