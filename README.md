# East London Mosque Adhan

<!-- ha-marketplace:exclude-start -->
[![Open in the Marketplace][my-marketplace-badge]][my-marketplace]
[![Validate][validate-badge]][validate] [![Tests][tests-badge]][tests]
<!-- ha-marketplace:exclude-end -->

Prayer times and the **live adhan from East London Mosque**, in Home Assistant.

- **Prayer times:** the mosque's own timetable (London Unified Prayer Times): the current prayer,
  when each prayer next begins, jamā‘ah times, and the Islamic date. Entities change exactly at
  each prayer time.
- **Live adhan:** whether the mosque is broadcasting right now, and the URL of its live Mixlr
  stream, ready to play on any speaker.
- **Smart Adhan blueprint:** plays the live adhan on your speakers at every prayer time, and falls
  back to a recording when the mosque isn't on air.

Set up from the UI, with no configuration to fill in. It needs no browser, MQTT or extra services.

> Unofficial. Not affiliated with or endorsed by East London Mosque, London Salah Times or Mixlr.
> Prayer times are produced by [London Salah Times](https://londonsalahtimes.com/) and published by
> East London Mosque.

<!-- ha-marketplace:exclude-start -->
## Installation

**Home Assistant 2026.11 and newer:** select the **Open in the Marketplace** badge above, or go to
**Settings → Marketplace → Add from link** and enter `Tinkering247/ha-elm-adhan`. Then select
**Install**.

**Older versions, with HACS:** add `https://github.com/Tinkering247/ha-elm-adhan` as a custom
repository of type **Integration**, download it, and restart Home Assistant.

**Manual:** copy `custom_components/elm_adhan` into your `config/custom_components/` folder and
restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Getting started

1. **Add the integration.** After installing, the setup page opens by itself. Otherwise, go to
   **Settings → Devices & services → Add integration → East London Mosque Adhan**.

   [![Add the integration][my-setup-badge]][my-setup]

2. **Choose your Asr time** under **Configure**. It defaults to 1 mithl; choose 2 mithl for the
   Ḥanafī time.

3. **Import the Smart Adhan blueprint**, and create an automation from it with your speakers.

   [![Import the blueprint][my-blueprint-badge]][my-blueprint]

## Entities

All entities belong to one service device, **ELM Adhan**.

| Entity | State | Attributes |
|---|---|---|
| `sensor.elm_adhan_current_prayer` | `Fajr`, `Sunrise`, `Zuhr`, `Asr`, `Maghrib` or `Ishā`: the latest to begin (`Ishā` overnight) | `next_prayer`, `next_prayer_time`, timetable range |
| `sensor.elm_adhan_fajr`, `_sunrise`, `_zuhr`, `_asr`, `_maghrib`, `_isha` | When it next begins (timestamp) | `jamaah`; Asr also has `mithl_1` and `mithl_2` |
| `sensor.elm_adhan_fajr_jamaah` … `_isha_jamaah` | When the congregation next starts (timestamp). *Disabled by default* | |
| `sensor.elm_adhan_islamic_date` | e.g. `17 Jumāda Al-Ākhirah 1448`, as published by the mosque | `day`, `month`, `year` |
| `binary_sensor.elm_adhan_live` | `on` while the mosque is broadcasting and its stream answers | |
| `sensor.elm_adhan_stream_url` | The live stream URL. Off air, the last one that played | `live`, `source`, `last_live` |

## Configuration

No fields are needed to set it up. Under **Configure**:

| Option | Default | |
|---|---|---|
| Asr begins at | 1 mithl | 2 mithl is the Ḥanafī time. Both are always in the Asr sensor's attributes |
| Start the Islamic day at Maghrib | on | Off changes the Islamic date at midnight |
| Stream polling interval | 5 min | The blueprint re-checks every 15 s around prayer time anyway |

## Smart Adhan blueprint

At each prayer time, the blueprint:

1. Pauses any players you list under *Pause first*, such as a TV.
2. Re-checks Mixlr every 15 seconds for up to *Wait for the broadcast to start* (default 90 s),
   because the broadcast often starts a little after the prayer time.
3. Turns the speakers on, sets the volume (Fajr can have its own), and plays the live stream. If
   the mosque isn't on air, it plays your fallback recording instead.
4. Stops the speakers after *Stop after* minutes (default 30, and Fajr can have its own). The live
   broadcast carries on into the prayer and any talk.

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

## Examples

**A reminder before Maghrib:** the timestamp sensors work directly as time triggers, with an
offset.

```yaml
triggers:
  - trigger: time
    at:
      entity_id: sensor.elm_adhan_maghrib
      offset: "-00:10:00"
actions:
  - action: notify.notify
    data:
      message: "Maghrib in 10 minutes"
```

**Do something at every prayer:**

```yaml
triggers:
  - trigger: state
    entity_id: sensor.elm_adhan_current_prayer
    to: [Fajr, Zuhr, Asr, Maghrib, Ishā]
```

**A dashboard card:**

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

## Coming from London Unified Prayer Times (`lupt`)

Both read the same timetable from the same page, and `sensor.elm_adhan_current_prayer` uses the
same states as `lupt.lupt`, so a state trigger only needs its entity changed. Set **Asr begins at**
and **Start the Islamic day at Maghrib** to match your old settings.

| `lupt` | East London Mosque Adhan |
|---|---|
| `states('lupt.lupt')` | `states('sensor.elm_adhan_current_prayer')` |
| `state_attr('lupt.lupt', 'next_fajr')` | `states('sensor.elm_adhan_fajr')` |
| `state_attr('lupt.lupt', 'next_ishā')` | `states('sensor.elm_adhan_isha')` (likewise `sunrise`, `zuhr`, `asr`, `maghrib`) |
| `state_attr('lupt.lupt', 'islamic_date')` | `states('sensor.elm_adhan_islamic_date')` |

## How it gets its data

| What | From | How often |
|---|---|---|
| Prayer timetable | `eastlondonmosque.org.uk/prayer-times`: the mosque's published table for the year | Twice a day |
| On air, and the stream URL | `api.mixlr.com`: Mixlr's public channel API | Every 5 minutes (configurable), and every 15 s while the blueprint waits |
| Is audio flowing | The stream itself (`listen.mixlr.com`): the first 2 KB, then it hangs up | With each stream check while the mosque is live |

Nothing is sent other than these requests: no account, no API key, no data about your home. The
last good timetable is stored in Home Assistant, so a website outage or a restart changes nothing.

## Updating and removing

- **Updating:** new versions arrive as an update in **Settings → Updates**. After updating,
  restart Home Assistant (a repair reminds you). Home Assistant only loads an integration's code at
  startup.
- **Removing:** delete the integration under **Settings → Devices & services**, then uninstall it
  from the Marketplace and restart. Automations made from the blueprint stay until you delete them.

## Known limitations

- **One mosque.** This integration covers East London Mosque only: its timetable and its stream.
  Prayer times for elsewhere in London are close, but not the same.
- **The timetable runs a year at a time.** The mosque publishes each year's timetable on the same
  page. If the stored timetable is within two weeks of running out, a repair appears under
  **Settings → System → Repairs**. It clears itself once the new year's timetable is online.
- **It reads public pages, not an official API.** If the mosque's website or Mixlr change their
  layout, the integration can break until it is updated. When the website can't be read, the
  stored timetable keeps working.
- **Not every prayer is broadcast live.** When the mosque isn't on air, the blueprint plays your
  fallback recording.

## Troubleshooting

- **Live and stream URL unavailable:** Home Assistant can't reach `api.mixlr.com`. Check the logs.
- **Live stays off at prayer time:** compare with <https://eastlondonmosque.mixlr.com>. The
  stream URL sensor's `source` attribute says what the integration saw, for example `off air` or
  `stream not responding`.
- **Prayer entities unknown:** the stored timetable has run out (see *Known limitations*), or it
  was never fetched. Check **Settings → System → Repairs** and the logs.
- **Reporting a problem:** download diagnostics from the integration's page and attach them to an
  [issue](https://github.com/Tinkering247/ha-elm-adhan/issues).

<!-- ha-marketplace:exclude-start -->
## Development

```sh
pip install -r requirements_test.txt
pytest
```

The tests run against recorded copies of the mosque's timetable page and Mixlr's API (in
`tests/fixtures/`), with the clock frozen inside the 2026 timetable.
<!-- ha-marketplace:exclude-end -->

[validate]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml
[validate-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/validate.yml/badge.svg
[tests]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml
[tests-badge]: https://github.com/Tinkering247/ha-elm-adhan/actions/workflows/tests.yml/badge.svg
[my-marketplace]: https://my.home-assistant.io/redirect/marketplace_repository/?owner=Tinkering247&repository=ha-elm-adhan&category=integration
[my-marketplace-badge]: https://my.home-assistant.io/badges/marketplace_repository.svg
[my-setup]: https://my.home-assistant.io/redirect/config_flow_start/?domain=elm_adhan
[my-setup-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[my-blueprint]: https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FTinkering247%2Fha-elm-adhan%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Felm_adhan%2Fsmart_adhan.yaml
[my-blueprint-badge]: https://my.home-assistant.io/badges/blueprint_import.svg
