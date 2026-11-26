# Security policy

## Supported versions

Only the latest release gets security fixes.

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Report them privately through GitHub: **Security → Report a vulnerability** on this repository. You'll get an answer within 7 days. A fix or mitigation for a confirmed issue will follow as soon as possible, and you'll be credited in the release notes unless you'd rather not be.

## What this project does on your machine

ding-dong-agent is small on purpose, so you can read all of it (`dingdong.py`, `installer.py`) in a few minutes. Before you install it, here is what it does:

| Area | Behaviour |
|---|---|
| Files it writes | `~/.local/share/ding-dong-agent/`, `~/.local/bin/dingdong`, `~/.config/ding-dong-agent/`, `~/.cache/ding-dong-agent/`, plus the `hooks` key of `~/.config/devin/config.json`, `~/.claude/settings.json` and `~/.codex/hooks.json`, and the `ding-dong` skill folder (`~/.agents/skills`, `~/.claude/skills`). It writes a timestamped backup before changing any agent config file. `--dry-run` shows the changes first, and `--uninstall` reverts them |
| Commands it runs | Only the local audio player (`afplay`, `mpv`, `ffplay`, `pw-play`, `paplay`, `mpg123`), the duration probe (`afinfo` or `ffprobe`), the decoder used for loudness levelling (`afconvert` or `ffmpeg`, writing only to a temporary folder that is deleted after playback) and the notifier (`osascript` or `notify-send`). It never uses a shell (`subprocess` with argument lists, no `shell=True`), and hook input is never used as a command or a path |
| Network | Only in random/Christmas mode and for `track <URL>`: HTTPS GET requests to `www.myinstants.com` (listing pages and `.mp3` files), or to the URL you pass to `track`. Only `http(s)` URLs are accepted. Downloads must be audio and at most 6 MB, and they are stored as data files, never executed. Hooks themselves never wait on the network: downloads run in a background process |
| Data it sends | None. No telemetry and no accounts. The hook JSON (session id, working directory) is only read locally to name the project in the notification and to avoid playing the same event twice |
| Dependencies | Python standard library only. There is nothing to install from PyPI at runtime |
| Privileges | It runs as your user and never asks for `sudo` |

## How the repository is checked

- **CodeQL** (Python and GitHub Actions) runs on every push and pull request, and weekly.
- **[Cisco AI Defense skill-scanner](https://github.com/cisco-ai-defense/skill-scanner)** scans the agent skill for prompt injection, data exfiltration, capability escalation and similar risks, using the static, behavioural and trigger analysers with strict YARA rules. Its findings are uploaded to GitHub code scanning.
- **Bandit** and **Ruff** (including the `S` security rules) run in CI. The following checks are skipped on purpose, and the reasons are listed here:
  - `B404` / `B603` / `B607`: running the local audio player and notifier is the whole point of the tool. Arguments are always lists and never come from hook input.
  - `B310`: `urlopen` is only reached through `fetch()`, which rejects every scheme except `http(s)`.
  - `B311`: `random` is used to pick a funny sound, not for anything security-related.
  - `B110`: the hook entry point swallows errors on purpose, so a broken sound can never break the agent.
- **OpenSSF Scorecard** runs weekly and publishes its results.
- **Dependabot** keeps the GitHub Actions and the pinned CI tools up to date. Every action is pinned to a full commit SHA.
