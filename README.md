# East London Mosque Adhan for Home Assistant

[![hacs][hacs-badge]][hacs] [![Validate][validate-badge]][validate] [![Tests][tests-badge]][tests]

Play the **live adhan from East London Mosque** on your speakers at every prayer time, and fall
back to a local recording when the mosque isn't broadcasting. The mosque's own **prayer timetable**
is included, so nothing else is needed.

- **Prayer times:** the mosque publishes the year's London Unified Prayer Times on
  [its website](https://www.eastlondonmosque.org.uk/prayer-times). The integration reads that
  timetable twice a day and keeps the last good copy, so a website outage changes nothing. Entities
  update exactly at each prayer time.
- **Live adhan:** the mosque streams from the mimbar on
  [Mixlr](https://eastlondonmosque.mixlr.com). Each broadcast gets a new stream URL. The integration
  polls Mixlr's public API for the current one and checks that audio is actually flowing. It needs
  no browser, no MQTT and no cron job.

> Unofficial. Not affiliated with or endorsed by East London Mosque, London Salah Times or Mixlr.
> Prayer times are produced by [London Salah Times](https://londonsalahtimes.com/) and published by
> East London Mosque.

## Entities

| Entity | State | Attributes |
|---|---|---|
| `sensor.elm_adhan_current_prayer` | `Fajr`, `Sunrise`, `Zuhr`, `Asr`, `Maghrib` or `Ishā`: the latest to begin (`Ishā` overnight) | `next_prayer`, `next_prayer_time`, timetable range |
| `sensor.elm_adhan_fajr` … `sensor.elm_adhan_isha`, `sensor.elm_adhan_sunrise` | When each next begins (timestamp) | `jamaah`; Asr also has `mithl_1`, `mithl_2` |
| `sensor.elm_adhan_<prayer>_jamaah` | When the congregation next starts (timestamp). *Disabled by default* | |
| `sensor.elm_adhan_islamic_date` | e.g. `17 Jumāda Al-Ākhirah 1448`, as published by the mosque | `day`, `month`, `year` |
| `binary_sensor.elm_adhan_live` | `on` while the mosque is broadcasting and the stream answers | |
| `sensor.elm_adhan_stream_url` | The live stream URL. Off air, the last URL that played | `live`, `source`, `last_live` |

The timestamp sensors work directly as `time` triggers, for example
`trigger: time` with `at: sensor.elm_adhan_fajr`.

**Coming from London Unified Prayer Times (`lupt`)?** `sensor.elm_adhan_current_prayer` uses the
same state names as `lupt.lupt`, so a state trigger only needs its entity changed. Both read the
same timetable from the same page. Set **Asr begins at** and **Start the Islamic day at Maghrib**
in the options to match your old settings.

| `lupt` | East London Mosque Adhan |
|---|---|
| `states('lupt.lupt')` | `states('sensor.elm_adhan_current_prayer')` |
| `state_attr('lupt.lupt', 'next_fajr')` | `states('sensor.elm_adhan_fajr')` |
| `state_attr('lupt.lupt', 'next_ishā')` | `states('sensor.elm_adhan_isha')` (likewise `sunrise`, `zuhr`, `asr`, `maghrib`) |
| `state_attr('lupt.lupt', 'islamic_date')` | `states('sensor.elm_adhan_islamic_date')` |

### Dashboard example

```yaml
type: markdown
title: Prayer times
content: |
  **Now:** {{ states('sensor.elm_adhan_current_prayer') }} · {{ states('sensor.elm_adhan_islamic_date') }}

  | Prayer | Begins |
  |---|---|
  {% for p in ['fajr', 'sunrise', 'zuhr', 'asr', 'maghrib', 'isha'] -%}
  | {{ state_attr('sensor.elm_adhan_' ~ p, 'friendly_name') | replace('ELM Adhan ', '') }} | {{ as_timestamp(states('sensor.elm_adhan_' ~ p)) | timestamp_custom('%H:%M') }} |
  {% endfor %}
```

## Installation

### Marketplace (Home Assistant 2026.11 and newer)

[![Open in Marketplace][my-hacs-badge]][my-hacs]

1. Go to **Settings → Marketplace** and select **Add from link** (top right).
2. Enter `Tinkering247/ha-elm-adhan` and select **Add**. The first time, the Marketplace asks you
   to connect GitHub. That connection is read-only.
3. Open **East London Mosque Adhan**, select **Install**, then finish the setup page that opens.
   No restart is needed for the first install.

**Updating:** the Marketplace offers new versions as an update entity. After updating, restart Home
Assistant: a repair under **Settings → System → Repairs** reminds you. Home Assistant only loads an
integration's code at startup, so reloading the integration is not enough.

### HACS (before 2026.11)

1. In HACS, open the **⋮** menu, choose **Custom repositories**, and add
   `https://github.com/Tinkering247/ha-elm-adhan` with the type **Integration**.
2. Download it and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and pick **East London Mosque Adhan**.

### Manual

Copy `custom_components/elm_adhan` into your Home Assistant `config/custom_components/` folder and
restart.

## Configuration

No setup fields are needed. Under **Configure**:

| Option | Default | |
|---|---|---|
| Asr begins at | 1 mithl | Choose 2 mithl for the Ḥanafī time |
| Start the Islamic day at Maghrib | on | Off changes the Islamic date at midnight |
| Stream polling interval | 5 min | The blueprint re-checks every 15 s around prayer time anyway |

If the stored timetable is within two weeks of running out, for example at the end of the year
before the mosque publishes the next one, a repair issue appears under **Settings → System →
Repairs**. It clears itself once the new timetable is online.

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

It is triggered by `sensor.elm_adhan_current_prayer` by default. Any entity works, such as
`lupt.lupt`, as long as its states match the **Prayers** list.

| Input | Default |
|---|---|
| Prayer time entity | `sensor.elm_adhan_current_prayer` |
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
[hacs-badge]: https://img.shields.io/badge/Marketplace%20%2F%20HACS-Custom-41BDF5.svg
[validate]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml
[validate-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml/badge.svg
[tests]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml
[tests-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml/badge.svg
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=Tinkering247&repository=ha-elm-adhan&category=integration
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-blueprint]: https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FTinkering247%2Fha-elm-adhan%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Felm_adhan%2Fsmart_adhan.yaml
[my-blueprint-badge]: https://my.home-assistant.io/badges/blueprint_import.svg
