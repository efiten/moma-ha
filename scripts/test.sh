#!/usr/bin/env bash
# Draait de volledige testsuite, inclusief laag 2.
#
# Home Assistants testharnas is Unix-only -- het importeert `fcntl` -- dus op
# Windows kan dit niet rechtstreeks. Draai het daar via WSL:
#
#     wsl -- bash scripts/test.sh -q
#
# De snelle laag-1-tests hebben Home Assistant niet nodig en draaien overal:
#
#     python -m pytest tests/protocol
#
# De venv komt bewust in $HOME en niet in de repo: op Windows-hosts staat de
# repo onder /mnt/c, en een venv daar is merkbaar langzamer.
set -euo pipefail

VENV="${MOMA_VENV:-$HOME/venv-moma}"

# Controleren op pytest en niet op bin/python: een half aangemaakte venv heeft
# de interpreter wel en de pakketten niet, en zou dan stilzwijgend overgeslagen
# worden.
if [ ! -x "$VENV/bin/pytest" ]; then
  echo "venv aanmaken in $VENV"
  rm -rf "$VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet \
    pytest pytest-asyncio pytest-homeassistant-custom-component
fi

cd "$(dirname "$0")/.."
exec "$VENV/bin/python" -m pytest "$@"
