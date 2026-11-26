#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path

APP = "ding-dong-agent"
CLI = "dingdong"
SKILL = "ding-dong"
HOME = Path.home()
REPO = Path(__file__).resolve().parent
OWN_COMMAND = re.compile(r'^"[^"]*/(dingdong|notify-sound)" (done|input) --agent (devin|claude|codex)$')
SKILL_MARKER = ".installed-by-" + APP
SHIM_MARKER = "# installed-by-" + APP


def agent_targets(home, env=None):
    env = os.environ if env is None else env
    codex_home = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else home / ".codex"
    return {
        "devin": {
            "settings": home / ".config/devin/config.json",
            "skills": home / ".agents/skills",
            "detect": [home / ".config/devin", home / ".local/share/devin"],
            "hooks": [
                ("Stop", "", "done", {}),
                ("PermissionRequest", "", "input", {}),
                ("PreToolUse", "^ask_user_question$", "input", {}),
            ],
        },
        "claude": {
            "settings": home / ".claude/settings.json",
            "skills": home / ".claude/skills",
            "detect": [home / ".claude"],
            "hooks": [
                ("Stop", "", "done", {"async": True}),
                ("PermissionRequest", "", "input", {"async": True}),
                ("PreToolUse", "^AskUserQuestion$", "input", {"async": True}),
            ],
        },
        "codex": {
            "settings": codex_home / "hooks.json",
            "skills": home / ".agents/skills",
            "detect": [codex_home],
            "hooks": [
                ("Stop", "", "done", {}),
                ("PermissionRequest", "", "input", {}),
            ],
        },
    }


def ours(handler):
    return isinstance(handler, dict) and bool(OWN_COMMAND.match(str(handler.get("command", ""))))


def strip_ours(hooks):
    cleaned = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            cleaned[event] = groups
            continue
        kept_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            handlers = [h for h in group["hooks"] if not ours(h)]
            if handlers:
                kept_groups.append(dict(group, hooks=handlers))
        if kept_groups:
            cleaned[event] = kept_groups
    return cleaned


def own_hooks(definitions, command, agent):
    hooks = {}
    for event, matcher, kind, extra in definitions:
        handler = dict({"type": "command", "command": f'"{command}" {kind} --agent {agent}', "timeout": 10}, **extra)
        group = {"matcher": matcher, "hooks": [handler]} if matcher else {"hooks": [handler]}
        hooks.setdefault(event, []).append(group)
    return hooks


def merge(hooks, extra):
    for event, groups in extra.items():
        hooks.setdefault(event, []).extend(groups)
    return hooks


def load_json(path):
    if not path.exists() or not path.read_text().strip():
        return {}
    return json.loads(path.read_text())


def backup(path):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for counter in range(1000):
        suffix = f".bak-{APP}-{stamp}" + (f"-{counter}" if counter else "")
        candidate = path.with_name(path.name + suffix)
        if not candidate.exists():
            shutil.copy2(path, candidate)
            return candidate
    raise RuntimeError(f"too many backups of {path}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and load_json(path) == data:
        return False
    if path.exists():
        print(f"  backup {backup(path)}")
    mode = path.stat().st_mode if path.exists() else None
    path.write_text(json.dumps(data, indent=2) + "\n")
    if mode is not None:
        os.chmod(path, stat.S_IMODE(mode))
    return True


def configure_hooks(target, command, agent, uninstall, dry_run):
    settings = target["settings"]
    existed = settings.exists()
    data = load_json(settings)
    mine = {} if uninstall else own_hooks(target["hooks"], command, agent)
    if dry_run:
        print(f"  would {'remove our hooks from' if uninstall else 'add these hooks to'} {settings}")
        if mine:
            print("    " + json.dumps(mine, indent=2).replace("\n", "\n    "))
        return
    hooks = merge(strip_ours(data.get("hooks", {})), mine)
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    if uninstall and existed and not data and settings.name == "hooks.json":
        settings.unlink()
        print(f"  removed empty {settings}")
        return
    changed = write_json(settings, data)
    verb = "removed from" if uninstall else "written to"
    print(f"  hooks {verb} {settings}" if changed else f"  hooks already up to date in {settings}")


def install_skill(skills_dir, uninstall, dry_run, force):
    destination = skills_dir / SKILL
    owned = (destination / SKILL_MARKER).exists()
    if dry_run:
        print(f"  would {'remove' if uninstall else 'copy'} skill {destination}")
        return
    if destination.exists() and not owned and not force:
        print(f"  skipped {destination}: it exists and wasn't installed by {APP} (use --force)")
        return
    if destination.exists():
        shutil.rmtree(destination)
    if uninstall:
        print(f"  skill removed from {destination}")
        return
    shutil.copytree(REPO / "skill" / SKILL, destination)
    (destination / SKILL_MARKER).write_text("")
    print(f"  skill copied to {destination}")


def shim_is_ours(path):
    return SHIM_MARKER in path.read_text(errors="replace")


def install_core(prefix, bin_dir, uninstall, dry_run, force):
    core = prefix / "dingdong.py"
    shim = bin_dir / CLI
    if dry_run:
        print(f"would {'remove' if uninstall else 'install'} {core} and {shim}")
        return shim
    if shim.exists() and not shim_is_ours(shim) and not force:
        sys.exit(f"{shim} exists and wasn't installed by {APP}; remove it or pass --force")
    if uninstall:
        for path in (core, shim):
            if path.exists():
                path.unlink()
        if prefix.exists() and not any(prefix.iterdir()):
            prefix.rmdir()
        return shim
    prefix.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "dingdong.py", core)
    python = shutil.which("python3") or sys.executable
    shim.write_text(
        "#!/bin/sh\n"
        f"{SHIM_MARKER}\n"
        f'for py in "{python}" "$(command -v python3)" /usr/bin/python3; do\n'
        f'  [ -n "$py" ] && [ -x "$py" ] && exec "$py" "{core}" "$@"\n'
        "done\n"
        f'echo "{APP}: python3 not found" >&2\n'
        "exit 1\n"
    )
    shim.chmod(0o755)
    print(f"installed {core}\ninstalled {shim}")
    return shim


def remove_legacy(home, dry_run):
    legacy = [home / ".local/bin/notify-sound", home / ".local/share/agent-notify-sound/notify_sound.py"]
    for path in legacy:
        if path.exists() and not dry_run and (path.suffix == ".py" or "agent-notify-sound" in path.read_text()):
            path.unlink()
            print(f"removed old agent-notify-sound file {path}")
    old_prefix = home / ".local/share/agent-notify-sound"
    if not dry_run and old_prefix.is_dir() and not any(old_prefix.iterdir()):
        old_prefix.rmdir()


def main():
    parser = argparse.ArgumentParser(
        description="Install ding-dong-agent hooks and skill for Devin, Claude Code and Codex."
    )
    parser.add_argument(
        "--agents", default="auto", help="comma-separated: devin,claude,codex (default: the ones found)"
    )
    parser.add_argument("--prefix", default=str(HOME / ".local/share" / APP))
    parser.add_argument("--bin-dir", default=str(HOME / ".local/bin"))
    parser.add_argument("--no-skill", action="store_true", help="install hooks only")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force", action="store_true", help="replace a dingdong command or skill folder we didn't create"
    )
    args = parser.parse_args()
    if sys.platform != "darwin" and not sys.platform.startswith("linux"):
        sys.exit(f"{APP} supports macOS and Linux")
    targets = agent_targets(HOME)
    if args.agents == "auto":
        selected = [name for name, target in targets.items() if any(p.exists() for p in target["detect"])]
    else:
        selected = [name.strip() for name in args.agents.split(",") if name.strip()]
    unknown = [name for name in selected if name not in targets]
    if unknown:
        sys.exit(f"unknown agent(s): {', '.join(unknown)}; use devin, claude or codex")
    if not selected:
        sys.exit("no supported agent found; pass --agents devin,claude,codex")
    shim = install_core(Path(args.prefix), Path(args.bin_dir), args.uninstall, args.dry_run, args.force)
    skill_dirs = []
    for name in selected:
        print(name)
        configure_hooks(targets[name], shim, name, args.uninstall, args.dry_run)
        if targets[name]["skills"] not in skill_dirs:
            skill_dirs.append(targets[name]["skills"])
    if not args.no_skill:
        print("skills")
        for skills_dir in skill_dirs:
            install_skill(skills_dir, args.uninstall, args.dry_run, args.force)
    if not args.uninstall:
        remove_legacy(HOME, args.dry_run)
    if args.uninstall or args.dry_run:
        return
    print(f"\nDing dong! Try it: {shim} test")
    if "codex" in selected:
        print(f"Codex: open /hooks once and trust the {CLI} hooks, otherwise Codex skips them.")
    if "devin" in selected or "claude" in selected:
        print("Devin / Claude Code: new sessions pick up the hooks (check with /hooks).")


if __name__ == "__main__":
    main()
