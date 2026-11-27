# East London Mosque Adhan for Home Assistant

[![hacs][hacs-badge]][hacs] [![Validate][validate-badge]][validate] [![Tests][tests-badge]][tests]

Play the **live adhan from East London Mosque** on your speakers at every prayer time, and fall
back to a local recording when the mosque isn't broadcasting.

The mosque streams from the mimbar on [Mixlr](https://eastlondonmosque.mixlr.com). Each broadcast
gets a new stream URL. This integration polls Mixlr's public API for the current one, checks that
audio is actually flowing, and exposes the result as Home Assistant entities. It needs no browser,
no MQTT and no cron job.

> Unofficial. Not affiliated with or endorsed by East London Mosque or Mixlr.

## Entities

| Entity | State | Attributes |
|---|---|---|
| `binary_sensor.elm_adhan_live` | `on` while the mosque is broadcasting and the stream answers | |
| `sensor.elm_adhan_stream_url` | The live stream URL. Off air, the last URL that played | `live`, `source`, `last_live` |

## Installation

### HACS (recommended)

[![Open in HACS][my-hacs-badge]][my-hacs]

1. In HACS, search for **East London Mosque Adhan** and download it.
   (Until it is in the default store: open the **⋮** menu, choose **Custom repositories**, and add
   `https://github.com/Tinkering247/ha-elm-adhan` with the type **Integration**.)
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and pick **East London Mosque Adhan**.

### Manual

Copy `custom_components/elm_adhan` into your Home Assistant `config/custom_components/` folder and
restart.

## Configuration

No setup fields are needed. Under **Configure** you can change the polling interval
(default 5 minutes, range 1–60). The blueprint re-checks every 15 seconds around prayer time, so
the polling interval only affects how up to date the sensors are the rest of the day.

## Blueprint: Smart Adhan

[![Import blueprint][my-blueprint-badge]][my-blueprint]

At each prayer time the blueprint:

1. Re-checks Mixlr every 15 seconds for up to *Wait for the broadcast to start* (default 90 s),
   because the broadcast often starts a little after the adhan time.
2. Sets the speaker volume, if you chose one.
3. Plays the live stream if the mosque is on air. Otherwise it plays your fallback recording.

It is triggered by an entity whose state changes to the prayer name, such as `lupt.lupt` from
London Unified Prayer Times. Any entity works, as long as its states match the **Prayers** list.

| Input | Default |
|---|---|
| Prayer time entity | *(required)* |
| Prayers | `Fajr`, `Zuhr`, `Asr`, `Maghrib`, `Ishā` |
| Speaker | *(required)* |
| Volume | `0.5` (`0` leaves it unchanged) |
| Fallback adhan | *(empty: play nothing)* |
| Wait for the broadcast to start | `90` s |

## Troubleshooting

- **Entities unavailable**: Home Assistant can't reach `api.mixlr.com`. Check the logs, and
  download diagnostics from the integration page.
- **Live stays off at prayer time**: compare with <https://eastlondonmosque.mixlr.com>. The
  sensor's `source` attribute says what the resolver saw, for example `off air` or
  `stream not responding`.

## Development

```sh
pip install -r requirements_test.txt
pytest
```

[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[validate]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml
[validate-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml/badge.svg
[tests]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml
[tests-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml/badge.svg
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=Tinkering247&repository=ha-elm-adhan&category=integration
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-blueprint]: https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FTinkering247%2Fha-elm-adhan%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Felm_adhan%2Fsmart_adhan.yaml
[my-blueprint-badge]: https://my.home-assistant.io/badges/blueprint_import.svg
