"""Opzet voor de tests van laag 2, de Home Assistant-lijm.

Deze tests hebben Home Assistant nodig; die van `tests/protocol/` niet. Die
scheiding is geen ordening om de ordening: de snelle CI-job installeert geen
Home Assistant, dus als er ooit een HA-import in laag 1 sluipt, valt die job om.
De grens uit ontwerpbeslissing 2 wordt zo door CI afgedwongen.
"""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat Home Assistant `custom_components/` inlezen tijdens tests."""
    yield
