---
name: ding-dong
description: Ding dong, your agent is at the door. Change, test or mute the sound and popup that Devin, Claude Code or Codex play when they finish a turn or need your input. Modes are one fixed track (local file, URL or system sound), random fun sounds from myinstants.com (global, trending, a category or a search), Christmas mode, or off. Use when the user asks to change, test, mute, randomise or theme the finish/notification sound.
license: MIT
---

# ding-dong

The ding-dong-agent hooks run `dingdong done` when a turn finishes and `dingdong input` when the agent waits for an approval or an answer. Everything goes through one CLI, `dingdong`, installed in `~/.local/bin`. If it isn't on `PATH`, use `~/.local/bin/dingdong`.

| User wants | Run |
|---|---|
| See the current setup | `dingdong status` |
| Hear it now | `dingdong test` or `dingdong test input` |
| One fixed sound | `dingdong track <sound> [<sound for input>]`, where a sound is a file path, a URL or a system sound name |
| A sound from a myinstants.com page | `dingdong track https://www.myinstants.com/en/instant/<name>/` |
| Random fun mode | `dingdong random <category>` |
| Random sounds matching words | `dingdong random "search:<words>"`, e.g. `"search:air horn"` |
| Christmas mode (Christmas sounds and song snippets, max 15 s) | `dingdong christmas` |
| Which categories exist | `dingdong categories` |
| Silence / sound back | `dingdong mute` / `dingdong unmute` |
| Tweak a setting | `dingdong set KEY VALUE` |
| Download more random sounds now | `dingdong refill <category> [count]` |
| Check loudness levelling | `dingdong levels [category or file]` |
| Version | `dingdong version` |

**Random categories:** `global`, `trending`, `any` (a different category each time), or one of:
- `anime & manga`, `games`, `memes`, `movies`, `music`, `politics`, `pranks`;
- `reactions`, `sound effects`, `sports`, `television`, `tiktok trends`, `viral`, `whatsapp audios`;
- `search:<words>`.

## Settings

Settings live in `~/.config/ding-dong-agent/config`:

| Key | Meaning |
|---|---|
| `MODE` | `track`, `random`, `christmas` or `off` |
| `DONE_SOUND` / `INPUT_SOUND` | Track mode sounds: an absolute file path or a system sound name. macOS has Glass, Hero, Ping, Submarine…; Linux uses freedesktop names such as `complete` or `message` |
| `DONE_CATEGORY` / `INPUT_CATEGORY` | Random mode categories |
| `INPUT_MODE` | Blank means the same as `MODE`. Set it to `track` to keep a calm approval sound while "finished" is random. `MODE=off` silences both |
| `MIN_DURATION` / `MAX_DURATION` | Random mode only keeps sounds of this length, in seconds (default 3–10) |
| `MAX_SECONDS` | Track and random sounds are cut off after this many seconds |
| `CHRISTMAS_QUERIES` | Comma-separated myinstants searches used by Christmas mode |
| `CHRISTMAS_MIN_DURATION` / `CHRISTMAS_MAX_DURATION` | Clip lengths Christmas mode accepts (default 2–300 s, so full songs are fine) |
| `CHRISTMAS_MAX_SECONDS` | Christmas sounds are cut off after this many seconds (default 15) |
| `VOLUME` | From 0 to 1, applied after levelling |
| `NORMALIZE` | `1` levels every sound to `TARGET_LEVEL`, `0` plays files as they are |
| `TARGET_LEVEL` | Loudness in dB every sound is brought to (default -22; -26 is quieter, -18 louder) |
| `MAX_BOOST` | Most a quiet sound is turned up (default ×4). Sounds are never boosted into clipping |
| `NOTIFY` | `1` shows a desktop notification, `0` plays the sound only |
| `MAX_PAGE` | Random sounds come from the first N pages (lower means more popular) |
| `CACHE_SIZE` | How many random sounds are kept per category |
| `DEDUPE_SECONDS` | The same event from the same session within this window plays only once |

## Rules

- **After any change**, run `dingdong test` so the user hears the result, and tell them what played.
- **Uneven volume:** if the user says sounds are too loud or too quiet overall, change `TARGET_LEVEL`, not `VOLUME`. If one sound still stands out, check `dingdong levels`.
- **Random mode warning:** random and search sounds are user-uploaded and can be loud, rude or NSFW. Before switching a user to random mode, mention that, and suggest `dingdong christmas`, a calm category such as `sound effects`, or a low `VOLUME` if kids or colleagues are around.
- **No network in the hooks:** URLs are downloaded once into `~/.config/ding-dong-agent/sounds/`. Random mode plays from the cache in `~/.cache/ding-dong-agent/` and refills it in the background.
- **One sound at a time** across all sessions on the machine. If another session finishes while a sound is still playing, it only shows the desktop notification, so nothing overlaps or gets cut off.
- **Unsupported sources:** streaming services and DRM-protected files can't be played.
- **Hook configuration:** don't edit the agents' hook configuration by hand. Re-run the project's `install.sh`, or `install.sh --uninstall`, instead.
