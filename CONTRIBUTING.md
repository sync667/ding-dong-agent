# Contributing

Thanks for helping. Ideas, bug reports and pull requests are all welcome.

## Ground rules

- Keep runtime code to the Python standard library and Python 3.8+. That is the reason it installs anywhere in one command.
- Hooks must stay fast and must never fail the agent:
  - no network in the hook path;
  - anything slow runs in a background process;
  - errors are swallowed in the `done` / `input` entry point.
- Every change in behaviour comes with a test in `tests/`.
- Don't add telemetry or calls to new hosts.

## Development

```sh
python3 -m venv .venv && . .venv/bin/activate   # dev tools need Python 3.10+
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check . && ruff format --check .
bandit -c pyproject.toml -r .
skill-scanner scan-all skill --recursive --use-behavioral --use-trigger --yara-mode strict --format summary
./install.sh --dry-run --agents devin,claude,codex
```

To try a change for real, run `./install.sh` (it can be run again and again), then `dingdong test`.

## Pull requests

- Keep each pull request to one topic and describe what changed for users.
- Update `README.md`, `skill/ding-dong/SKILL.md` and `CHANGELOG.md` when commands or settings change.
- CI has to pass (tests on Linux and macOS, lint, Bandit, CodeQL and the skill scan).
