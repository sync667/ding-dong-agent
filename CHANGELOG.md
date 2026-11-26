# Changelog

## 1.3.0

- **Loudness levelling:**
  - every sound is measured and scaled to the same loudness before it plays, so quiet clips are turned up and loud ones turned down;
  - new settings: `NORMALIZE`, `TARGET_LEVEL` (default -22 dB) and `MAX_BOOST` (default ×4);
  - gain is capped by each clip's peak, so it never clips;
  - this runs in the background player, so hooks stay at about 0.1 s.
- **`dingdong levels`** shows the measured loudness and the gain used for each sound.
- **Easier install:**
  - one line: `curl -fsSL https://raw.githubusercontent.com/sync667/ding-dong-agent/v1.3.0/install.sh | sh`. Piped into `sh`, `install.sh` downloads the tagged release into a temporary folder, runs the installer from there and cleans up;
  - or paste the prompt from the README into your agent and let it install for you, with a dry run first.

## 1.2.0

- **New name:** the project is now **ding-dong-agent**, the command is `dingdong` and the skill is `ding-dong`. The installer replaces the old `agent-notify-sound` hooks and command automatically.
- **Mute fixed:** `mute` (`MODE=off`) now also silences approval sounds when `INPUT_MODE` is set.
- **Safer installer:**
  - it only touches hooks that exactly match the command it writes, and keeps every other hook and odd entry as is;
  - backup names are always unique;
  - `--dry-run` prints only this tool's hooks;
  - it doesn't overwrite a skill folder or `dingdong` command it didn't create, unless you pass `--force`;
  - `CODEX_HOME` is respected;
  - the skill is installed once into `~/.agents/skills` for Devin and Codex.
- **Sturdier hooks:** a broken config, cache file or player no longer stops the notification.
- **`global` source:** `global` now uses myinstants' "best of all time" list, because the old index page redirects to trending.
- **Linux:** `VOLUME` now also works with `pw-play`, `paplay` and `mpg123`. `aplay` was dropped, because it can't play mp3.
- **Clearer `test`:** `dingdong test` now explains why nothing played.
- **Downloads:** downloaded tracks get a short hash in their file name so they can't overwrite each other, and page downloads are capped at 2 MB.
- **CLI:** `refill` accepts categories with spaces, `unmute` does nothing unless muted, and `version` was added.
- **Christmas filter:** fewer false positives (no more "natal" or "noel" in unrelated titles).
- **README:** added a warnings section. Random mode can get spicy, so read it before you turn it on with kids around.

## 1.1.0

- **Christmas mode** (`dingdong christmas`): plays random Christmas sounds and song snippets from myinstants.com, each cut off after 15 seconds (`CHRISTMAS_MAX_SECONDS`).
- **Search sources:** random mode can now use a search with `random search:<words>`.
- **One sound at a time:** if another session finishes while a sound is still playing, it now shows only the notification. Sounds no longer overlap or cut each other off.
- **Duplicate detection** is now keyed by session, so two sessions finishing at the same moment each get their notification.
- **Downloads:** search pages that don't exist are skipped, and the download limit was raised to 6 MB so longer songs fit.

## 1.0.0

- Hooks for Devin, Claude Code and Codex, a `dingdong` CLI and an agent skill.
- **Track mode:** a local file, a URL, a myinstants page or a system sound.
- **Random mode:** a myinstants category, global, trending or any, limited to clips of 3–10 seconds.
- **Desktop notifications** that show the agent, the project and the sound title.
