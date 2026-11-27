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

### Marketplace (Home Assistant 2026.11 and newer)

[![Open in Marketplace][my-hacs-badge]][my-hacs]

1. Go to **Settings → Marketplace** and select **Add from link** (top right).
2. Enter `Tinkering247/ha-elm-adhan` and select **Add**. The first time, the Marketplace asks you
   to connect GitHub. That connection is read-only.
3. Open **East London Mosque Adhan**, select **Install**, then finish the setup page that opens.
   No restart is needed.

### HACS (before 2026.11)

1. In HACS, open the **⋮** menu, choose **Custom repositories**, and add
   `https://github.com/Tinkering247/ha-elm-adhan` with the type **Integration**.
2. Download it and restart Home Assistant.
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

1. Pauses any players you list under *Pause first*, such as a TV.
2. Re-checks Mixlr every 15 seconds for up to *Wait for the broadcast to start* (default 90 s),
   because the broadcast often starts a little after the adhan time.
3. Turns the speakers on, sets the volume (a separate Fajr volume is optional), and plays the live
   stream. If the mosque isn't on air, it plays your fallback recording instead.
4. Stops the speakers after *Stop after* minutes (default 30; Fajr can have its own value). The
   live broadcast carries on into the prayer and any talk.

It is triggered by an entity whose state changes to the prayer name, such as `lupt.lupt` from
London Unified Prayer Times. Any entity works, as long as its states match the **Prayers** list.

| Input | Default |
|---|---|
| Prayer time entity | *(required)* |
| Prayers | `Fajr`, `Zuhr`, `Asr`, `Maghrib`, `Ishā` |
| Speakers (`media_player.play_media`) | *(none)* |
| Speakers that need Media Extractor (`media_extractor.play_media`) | *(none)* |
| Pause first | *(none)* |
| Volume / Fajr volume | `0.4` / same as Volume (`0` leaves it unchanged) |
| Stop after / at Fajr | `30` min / same as Stop after (`0` never stops) |
| Fallback adhan | *(empty: play nothing)* |
| Wait for the broadcast to start | `90` s |

Some Google Cast speakers only play Mixlr streams through
[Media Extractor](https://www.home-assistant.io/integrations/media_extractor/). If a Cast speaker
stays silent, move it to *Speakers that need Media Extractor*.

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
