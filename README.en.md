# MoMa for Home Assistant

[Nederlands](README.md) · **English**

[![HACS: custom repository](https://img.shields.io/badge/HACS-custom%20repository-41BDF5.svg)](https://hacs.xyz)
[![Home Assistant 2025.1+](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41BDF5.svg)](https://www.home-assistant.io)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Home Assistant integration for the **MoMa** by
[Smart-E-Grid](https://smartegrid.be) — power, battery charge and grid
frequency, straight off your own network.

There is nothing to configure. The MoMa announces itself on your network, so you
do not need to look up an IP address, enter a password or create an account.
Nothing leaves your home either: it all stays local.

## Installing

Two buttons. The first adds this integration to HACS, the second sets it up.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=moma-ha&owner=efiten&category=Integration)

Click **Download**, then **restart Home Assistant**. After that:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=moma)

The port is pre-filled with 8484 — leave it unless you know it was changed. Your
device shows up within about five seconds.

> The buttons ask once for the address of your own Home Assistant. If they do
> not work for you, use the manual steps below.

<details>
<summary><b>Installing manually</b></summary>

**Through HACS.** HACS → ⋮ top right → *Custom repositories* → URL
`https://github.com/efiten/moma-ha`, category **Integration** → *Add*. Then
search for *Smart-E-Grid MoMa*, click **Download** and restart Home Assistant.

**Without HACS.** Copy the `custom_components/moma/` folder from this repository
into the `custom_components/` folder of your Home Assistant configuration, and
restart.

**Setting up.** Settings → Devices & Services → **Add integration** →
*Smart-E-Grid MoMa*.

</details>

## What you get

One device per MoMa, with a sensor for each measurement:

| Sensor | Unit | Meaning |
|---|---|---|
| Grid power | W | Exchange with the grid — **positive is consumption, negative is export** |
| Home power | W | What the house consumes |
| PV power | W | What the solar panels produce |
| Battery power | W | **Positive is charging, negative is discharging** |
| Battery SOC | % | Battery state of charge |
| Frequency | Hz | Grid frequency |

If a firmware update gives your MoMa extra fields, they show up as sensors on
their own. That does not need a new version of this integration.

## No device appears, or no sensors

**A device but no sensors.** That is normal for an installation that is not
doing anything yet. A measurement only becomes a sensor once it reports
something other than zero — otherwise you would end up with sensors for hardware
you do not have. You will also see a note about this under *Settings → Repairs*.
It resolves itself as soon as the installation starts measuring.

To see them right away: Devices & Services → **Smart-E-Grid MoMa** → *Configure*
→ **Show all fields**. Sensors created that way do not disappear when you switch
the option back off.

**No device at all.** Then the MoMa's announcement is not reaching Home
Assistant. Usually that is the network:

- Home Assistant has to be on the **same network** as the MoMa. The announcement
  is a broadcast and does not cross a router.
- If Home Assistant runs in Docker, it needs `--network host`. Broadcasts do not
  arrive on a bridge network.
- A guest network or VLAN separation between the two blocks the traffic.

**Everything went unavailable.** After a minute without a message the
integration marks the sensors as unavailable. They come back on their own as
soon as the MoMa sends something again.

**Reporting a problem.** The integration page has a **Download diagnostics**
button. That file describes exactly what came in, with the serial number and IP
address stripped out, so it can go straight into an
[issue](https://github.com/efiten/moma-ha/issues).

## Further reading

Written in Dutch, since that is the working language of this project:

- [`docs/ontwikkelen.md`](docs/ontwikkelen.md) — contributing: layout, tests,
  and the capture tooling
- [`docs/protocol.md`](docs/protocol.md) — how the MoMa announces itself
- [`docs/ontwerpbeslissingen.md`](docs/ontwerpbeslissingen.md) — the decisions
  made, and why
- [`docs/veldnaamconventie.md`](docs/veldnaamconventie.md) — for the device
  manufacturer: which field names are rendered correctly on their own

## Licence

MIT — see [LICENSE](LICENSE).
