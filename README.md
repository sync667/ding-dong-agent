<p align="center">
  <img src="assets/logo.png" alt="ding-dong-agent logo: a yellow bell with a terminal prompt" width="180">
</p>

# ding-dong-agent 🔔

[![CI](https://github.com/sync667/ding-dong-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sync667/ding-dong-agent/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sync667/ding-dong-agent/actions/workflows/codeql.yml/badge.svg)](https://github.com/sync667/ding-dong-agent/actions/workflows/codeql.yml)
[![Skill security scan](https://github.com/sync667/ding-dong-agent/actions/workflows/skill-scan.yml/badge.svg)](https://github.com/sync667/ding-dong-agent/actions/workflows/skill-scan.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/sync667/ding-dong-agent/badge)](https://scorecard.dev/viewer/?uri=github.com/sync667/ding-dong-agent)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Ding dong, your agent is at the door.**

You have nine terminals open: Devin is refactoring, Claude is writing tests, Codex is "just checking one thing", and a fourth agent has been politely waiting for your approval for twenty minutes. Meanwhile you're making coffee and wondering where to put your sweet hands next.

**ding-dong-agent** rings when an agent **finishes a turn** or **needs you**, plays a sound and pops up a notification that tells you exactly which agent and which project:

```
┌──────────────────────────────────────────────┐
│ 🔔  Claude: payments-service                 │
│     Finished, check the session (Bruh)       │
└──────────────────────────────────────────────┘
```

It works with **Devin CLI**, **Claude Code** and **Codex**, on macOS and Linux.

## Modes

| Mode | What you hear |
|---|---|
| 🎵 **Track** | One sound you choose: a local file, a URL, a [myinstants.com](https://www.myinstants.com) page or a system sound (Glass, Hero, Ping…) |
| 🎲 **Random fun** | A different 3–10 second clip from myinstants.com every time: best of all time, trending, a category (memes, games, anime & manga, movies…) or a search such as `search:air horn` |
| 🎄 **Christmas** | Random Christmas sounds and song snippets, cut off after 15 seconds. Mariah would approve |
| 🤫 **Off** | Peace and quiet. The notifications still pop up if you want them |

**Every ding at the same loudness.** Some meme clips whisper and others blow your speakers. Each sound is measured and turned up or down to the same level (`TARGET_LEVEL`, -22 dB by default), so a quiet "wow" and a screaming air horn come out equally loud. Run `dingdong levels` to see the numbers.

**Nine sessions, one doorbell.** Only one sound plays at a time on your machine. If another session finishes while a sound is still playing, it shows only its notification, so sounds never overlap or cut each other off.

The repo also ships a **ding-dong skill**, so you can simply say *"switch my finish sound to random anime"* or *"mute the doorbell"* and your agent changes the setting itself.

---

## ⚠️ Warnings (please read, we mean it)

- 🧒 **Kids at home? Be careful with random mode.** The random sounds come from myinstants.com, where anyone can upload anything, and it can get **spicy**: swearing, screaming, "adult" moans, very loud memes. The category names don't guarantee anything. Around kids, a calm office or a video call:
  - stick to **track mode** or **Christmas mode**;
  - or choose a calmer category like `sound effects`;
  - or turn it down with `dingdong set VOLUME 0.3`.
- 🤢 **It can get yucky too.** Fart and burp compilations are a whole genre on myinstants. Hopefully nothing creepy, but we can't promise. If a sound haunts you, delete it from `~/.cache/ding-dong-agent/<category>/`.
- 📢 **Loud.** Some clips are recorded at "neighbour complaint" volume. `MAX_SECONDS` and `VOLUME` are your friends.
- 🎧 **Screen sharing and meetings.** Your colleagues will hear "BRUH" exactly when the demo goes wrong. Run `dingdong mute` before you present.
- 🎄 **Christmas mode is seasonal.** Run `dingdong track Glass` in January, or you'll be singing "All I Want for Christmas" in July.
- ©️ **Copyright.** The sounds belong to their uploaders and owners. Keep them for personal fun and don't redistribute the cached files.

---

## Requirements

- **macOS** (uses `afplay`, `afinfo`, `afconvert` and `osascript`) or **Linux**, with one of `mpv`, `ffplay`, `pw-play`, `paplay` or `mpg123`.
  - Optional on Linux: `ffmpeg` and `ffprobe`, for loudness levelling and the random-mode length filter.
  - Optional on Linux: `notify-send`, for notifications.
- **Python 3.8+**. Only the standard library is used.
- At least one of:
  - [Devin CLI](https://devin.ai);
  - [Claude Code](https://claude.com/claude-code);
  - [Codex](https://developers.openai.com/codex) (the CLI or the desktop app, with hooks enabled, which is the default).

Windows isn't supported yet. PRs are welcome.

## Install

Pick one of three ways. They all run the same installer and end in the same place.

### Ask your agent

Paste this into Devin, Claude Code or Codex:

```text
Install ding-dong-agent from https://github.com/sync667/ding-dong-agent (tag v1.3.0).
Run its installer with --dry-run first and show me what it will change.
After I confirm, run it for real, then run `dingdong test`.
If Codex is installed, remind me to trust the two dingdong hooks in /hooks.
```

### One line

```sh
curl -fsSL https://raw.githubusercontent.com/sync667/ding-dong-agent/v1.3.0/install.sh | sh -s -- --dry-run   # see what would change
curl -fsSL https://raw.githubusercontent.com/sync667/ding-dong-agent/v1.3.0/install.sh | sh                   # install
dingdong test                                                                                                # ding dong!
```

The script downloads release `v1.3.0` over HTTPS into a temporary folder, runs the installer from there and deletes the folder. Any option below works after `sh -s --`, for example `sh -s -- --agents claude,codex`. Prefer to read it first? [It's short](install.sh).

### From a clone

```sh
git clone https://github.com/sync667/ding-dong-agent.git
cd ding-dong-agent
./install.sh                         # finds Devin, Claude Code and Codex automatically
./install.sh --agents claude,codex   # or choose the agents yourself
./install.sh --dry-run               # show what would change, without touching anything
dingdong test                        # ding dong!
```

### What the installer does

The installer does four things:

1. **Installs the command:** copies `dingdong.py` to `~/.local/share/ding-dong-agent/` and adds a `dingdong` command to `~/.local/bin/`.
2. **Adds hooks** to each agent's **user-level** config:
   - your other hooks stay as they are;
   - only hooks that exactly match the command it writes are ever replaced or removed;
   - a timestamped backup is written next to every file it changes.
3. **Copies the `ding-dong` skill.** Use `--no-skill` to skip this. It never overwrites a folder it didn't create, unless you pass `--force`.
4. **Can be run again at any time.** It doesn't create duplicate hooks. It also replaces hooks left by the old `agent-notify-sound` version.

| Agent | Hook file | "Finished" | "Needs you" | Skill folder |
|---|---|---|---|---|
| Devin | `~/.config/devin/config.json` | `Stop` | `PermissionRequest`, `PreToolUse` on `ask_user_question` | `~/.agents/skills/` |
| Claude Code | `~/.claude/settings.json` | `Stop` | `PermissionRequest`, `PreToolUse` on `AskUserQuestion` | `~/.claude/skills/` |
| Codex | `~/.codex/hooks.json` (or `$CODEX_HOME`) | `Stop` | `PermissionRequest` | `~/.agents/skills/` |

**After installing:**

- **Codex:** open `/hooks` once and **trust** the two `dingdong` hooks. Codex skips hooks you haven't reviewed. Your existing `notify = [...]` setting in `config.toml` isn't touched.
- **Devin and Claude Code:** new sessions pick up the hooks. Check with `/hooks`.

### Uninstall

```sh
./install.sh --uninstall                                  # removes hooks, skills and the command; keeps your settings and sounds
# no clone? curl -fsSL https://raw.githubusercontent.com/sync667/ding-dong-agent/v1.3.0/install.sh | sh -s -- --uninstall
rm -rf ~/.config/ding-dong-agent ~/.cache/ding-dong-agent   # also delete your settings and sounds
```

## Usage

```sh
dingdong status                        # current settings and cached sounds
dingdong test                          # play the "finished" sound now
dingdong test input                    # play the "needs you" sound now

dingdong track Hero                    # a system sound (macOS: Glass, Hero, Ping, Submarine, …)
dingdong track ~/Music/done.mp3        # a local file (mp3, m4a, wav, aiff, ogg)
dingdong track https://www.myinstants.com/en/instant/anime-wow/   # downloaded once, then played offline
dingdong track ~/Music/done.mp3 Ping   # a different sound for "needs you"

dingdong random memes                  # random fun mode, read the warnings first 🙃
dingdong random trending               # what's trending on myinstants
dingdong random any                    # a different category every time
dingdong random "search:air horn"      # random results of a myinstants search
dingdong christmas                     # 🎄 Christmas sounds and song snippets, max 15 s each
dingdong categories                    # list all categories
dingdong levels                        # loudness of the current sounds and the gain applied to each

dingdong set INPUT_MODE track          # random when finished, calm track sound for approvals
dingdong set MAX_DURATION 6            # only random clips up to 6 seconds
dingdong set VOLUME 0.5
dingdong mute                          # silence; unmute restores the previous mode
dingdong unmute
```

Or just ask your agent, and the `ding-dong` skill does the rest:

> *"Use random anime sounds when you finish, but keep Ping for approvals."*

**Random categories:** `global` (best of all time), `trending`, `any`, `anime & manga`, `games`, `memes`, `movies`, `music`, `politics`, `pranks`, `reactions`, `sound effects`, `sports`, `television`, `tiktok trends`, `viral`, `whatsapp audios`, or `search:<words>`.

### Christmas mode 🎄

`dingdong christmas` picks random results from several myinstants searches: christmas, jingle bells, xmas, merry christmas, all i want for christmas, last christmas, feliz navidad, ho ho ho and sleigh bells.

- **Only Christmas titles:** results whose title doesn't look Christmassy are skipped.
- **Song snippets:** full songs are fine, because every clip is cut off after `CHRISTMAS_MAX_SECONDS` (15 by default).
- **Calm approvals:** `dingdong set INPUT_MODE track` keeps a short sound for approvals.

## Settings

Settings are stored in `~/.config/ding-dong-agent/config`, one `KEY="value"` per line. Change them with `dingdong set` or edit the file. See [`examples/config`](examples/config) for a sample.

| Key | Default | Meaning |
|---|---|---|
| `MODE` | `track` | `track`, `random`, `christmas` or `off` (`off` also silences `INPUT_MODE`) |
| `DONE_SOUND` | `Glass` / `complete` | Track mode sound for "finished": a file path or a system sound name |
| `INPUT_SOUND` | `Ping` / `message` | Track mode sound for "needs you" |
| `DONE_CATEGORY` / `INPUT_CATEGORY` | `global` | Random mode categories |
| `INPUT_MODE` | *(same as `MODE`)* | Set to `track` to keep a calm approval sound while "finished" is random |
| `MIN_DURATION` / `MAX_DURATION` | `3` / `10` | Random mode only keeps clips of this length, in seconds |
| `MAX_SECONDS` | `10` | Track and random sounds are cut off after this many seconds |
| `CHRISTMAS_QUERIES` | *(see above)* | Comma-separated myinstants searches used by Christmas mode |
| `CHRISTMAS_MIN_DURATION` / `CHRISTMAS_MAX_DURATION` | `2` / `300` | Clip lengths Christmas mode accepts |
| `CHRISTMAS_MAX_SECONDS` | `15` | Christmas sounds are cut off after this many seconds |
| `VOLUME` | `1` | From 0 to 1, applied after levelling |
| `NORMALIZE` | `1` | `1` brings every sound to `TARGET_LEVEL`; `0` plays files as they are |
| `TARGET_LEVEL` | `-22` | Loudness every sound is brought to, in dB (gated RMS). Use `-26` for quieter or `-18` for louder |
| `MAX_BOOST` | `4` | Most a quiet sound can be turned up (×4 = +12 dB). Sounds are never boosted past the point where they would clip |
| `NOTIFY` | `1` | `0` turns off the notification and keeps only the sound |
| `MAX_PAGE` | `10` | Random sounds come from the first N pages (lower means more popular) |
| `CACHE_SIZE` | `30` | How many random sounds are kept per category |
| `DEDUPE_SECONDS` | `2` | The same event from the same session within this window plays only once |

## How it works

- **Hooks are fast and never wait for the network.**
  - Each hook runs `dingdong done|input --agent <name>`.
  - The command reads the hook JSON from stdin, starts the player and the notification in the background, and returns in about 0.1 s.
  - Random sounds are played from a local cache in `~/.cache/ding-dong-agent/<category>/`.
  - After each play, a background job downloads a few more sounds and keeps only clips of the right length.
  - If the cache is still empty (first use, or offline), the track sound plays instead.
  - Errors are swallowed, so a broken sound can never break your agent.
- **Levelled loudness.**
  - Before playing, the background player decodes the clip (with `afconvert` on macOS, or `ffmpeg` on Linux) to mono 32 kHz.
  - It measures the loudness, using RMS over 100 ms blocks with silence and relative gating, similar to LUFS.
  - It writes a temporary copy scaled to `TARGET_LEVEL`. The gain is capped by `MAX_BOOST` and by the clip's peak, so nothing clips.
  - The hook itself never waits for this. If decoding fails, the original file plays at `VOLUME`.
- **No overlapping sounds.**
  - A machine-wide lock allows only one player at a time.
  - If a sound is still playing when another session rings, that session shows only its notification.
- **No double dings.**
  - Devin also loads Claude Code's `~/.claude/settings.json` hooks. A Claude hook that runs inside Devin is recognised and skipped (there's no `transcript_path` and `DEVIN_PROJECT_DIR` is set).
  - The same event from the same session within `DEDUPE_SECONDS` plays only once.
- **Notification title.** It shows the agent and the project, for example *"Codex: my-repo"*. In random mode the message also includes the sound's title.
- **URLs are downloaded once.** Sounds from `track <url>` are saved in `~/.config/ding-dong-agent/sounds/`. Downloads must be audio files of at most 6 MB.

## Security

The tool runs inside your agents' hooks, so it is built to be boring to audit:

- **No runtime dependencies:** only the Python standard library.
- **No telemetry.**
- **No shell:** commands are always argument lists.
- **Network only for random and Christmas mode or `track <url>`**, and only to myinstants.com or the URL you give it.
- **Reversible installation:** the installer has `--dry-run`, backs up every config file it changes, and `--uninstall` reverts everything.

Each push is checked by CodeQL, the [Cisco AI Defense skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) (for the agent skill), Bandit, Ruff security rules and OpenSSF Scorecard, and every GitHub Action is pinned to a commit SHA. [SECURITY.md](SECURITY.md) has the full list of what the tool touches and how to report a vulnerability.

## Troubleshooting

| Problem | Check |
|---|---|
| No sound at all | Run `dingdong test`, which says why. On macOS check the output device and volume; on Linux install `mpv` or `ffplay` |
| No notification banner (macOS) | System Settings → Notifications → allow **Script Editor** (that's how `osascript` notifications appear) |
| Codex stays silent | Open `/hooks` in Codex and trust the `dingdong` hooks; check that `[features] hooks` isn't `false` |
| Devin / Claude stay silent | Open a new session; `/hooks` should list `dingdong … --agent …` |
| A second session made no sound | That's on purpose: another sound was still playing, so it showed only the notification |
| Random mode always plays the track sound | The cache is empty: run `dingdong refill memes 5` (needs internet) and check `dingdong status` |
| Random clips are too long on Linux | Install `ffprobe` (part of ffmpeg) so clip lengths can be checked |
| Some sounds are still louder than others | Run `dingdong levels`. Very quiet clips hit `MAX_BOOST` or their peak limit; raise `MAX_BOOST` or lower `TARGET_LEVEL`. On Linux, install `ffmpeg`, which is needed for levelling |
| A sound was too spicy | Delete it from `~/.cache/ding-dong-agent/<category>/`, choose a calmer category, or go back to `dingdong track Glass` |

## Development

```sh
python3 -m venv .venv && . .venv/bin/activate   # dev tools need Python 3.10+
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check . && ruff format --check . && bandit -c pyproject.toml -r .
skill-scanner scan-all skill --recursive --use-behavioral --use-trigger --yara-mode strict --format summary
./install.sh --dry-run --agents devin,claude,codex
```

The project has no dependencies outside the Python standard library and no build step. [CONTRIBUTING.md](CONTRIBUTING.md) has the ground rules.

## Credits and licence

- Random sounds come from [myinstants.com](https://www.myinstants.com). They are uploaded by users and belong to their owners.
- The project is released under the MIT licence, see [LICENSE](LICENSE). Ding dong. 🔔
