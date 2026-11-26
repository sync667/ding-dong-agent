#!/usr/bin/env python3
import array
import contextlib
import fcntl
import hashlib
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

VERSION = "1.3.0"
HOME = Path.home()
APP = "ding-dong-agent"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / APP
CONF = CONFIG_DIR / "config"
SOUNDS_DIR = CONFIG_DIR / "sounds"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / APP
MAC_SOUNDS = Path("/System/Library/Sounds")
LINUX_SOUNDS = Path("/usr/share/sounds/freedesktop/stereo")
BASE = "https://www.myinstants.com"
UA = "Mozilla/5.0 (compatible; " + APP + "/" + VERSION + ")"
CATEGORIES = [
    "anime & manga",
    "games",
    "memes",
    "movies",
    "music",
    "politics",
    "pranks",
    "reactions",
    "sound effects",
    "sports",
    "television",
    "tiktok trends",
    "viral",
    "whatsapp audios",
]
SPECIAL = {"global": "/en/best_of_all_time/us/", "trending": "/en/trending/us/"}
THEMES = ["christmas"]
CHRISTMAS_WORDS = re.compile(
    r"christmas|xmas|jingle|navidad|ho[ -]?ho[ -]?ho|sleigh|rudolph|merry (christmas|xmas)|weihnacht|santa ?claus"
    r"|snowman|mistletoe|feliz natal|joyeux no[eë]l",
    re.IGNORECASE,
)
AGENTS = {"devin": "Devin", "claude": "Claude", "codex": "Codex", "test": "Test"}
MODES = ["track", "random", "christmas", "off"]
DEFAULTS = {
    "MODE": "track",
    "DONE_SOUND": "Glass" if sys.platform == "darwin" else "complete",
    "INPUT_SOUND": "Ping" if sys.platform == "darwin" else "message",
    "DONE_CATEGORY": "global",
    "INPUT_CATEGORY": "global",
    "INPUT_MODE": "",
    "MIN_DURATION": "3",
    "MAX_DURATION": "10",
    "MAX_SECONDS": "10",
    "CHRISTMAS_QUERIES": ",".join(
        [
            "christmas",
            "jingle bells",
            "xmas",
            "merry christmas",
            "all i want for christmas",
            "last christmas",
            "feliz navidad",
            "ho ho ho",
            "sleigh bells",
        ]
    ),
    "CHRISTMAS_MIN_DURATION": "2",
    "CHRISTMAS_MAX_DURATION": "300",
    "CHRISTMAS_MAX_SECONDS": "15",
    "VOLUME": "1",
    "MAX_PAGE": "10",
    "CACHE_SIZE": "30",
    "NOTIFY": "1",
    "DEDUPE_SECONDS": "2",
    "NORMALIZE": "1",
    "TARGET_LEVEL": "-22",
    "MAX_BOOST": "4",
    "PREVIOUS_MODE": "",
}
MAX_BYTES = 6 * 1024 * 1024
MAX_PAGE_BYTES = 2 * 1024 * 1024
ANALYSIS_RATE = 32000
SAMPLE_FULL_SCALE = 32768.0
BLOCK_SECONDS = 0.1
SILENCE_GATE_DB = -70.0
RELATIVE_GATE_DB = -10.0
PEAK_CEILING = 0.97
USAGE = """usage: dingdong <command>

  status                         show settings and cached sounds
  test [done|input]              play the sound now
  track <sound> [<input sound>]  one track: file path, URL (mp3 or myinstants page) or system sound name
  random <category>              random sounds from myinstants.com: global, trending, any, a category or search:<words>
  christmas                      random Christmas sounds and song snippets (up to 15 s)
  categories                     list random categories
  set KEY VALUE                  change one setting
  mute | unmute                  turn sounds off or back on
  refill <category> [count]      download more random sounds now
  levels [category|file]         show loudness and the gain used to even it out
  version                        print the version
  done | input [--agent NAME]    hook entry points (read the hook JSON on stdin)
"""


def load_conf():
    conf = dict(DEFAULTS)
    if CONF.exists():
        for raw in CONF.read_text().splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                conf[key.strip()] = os.path.expandvars(os.path.expanduser(value.strip().strip('"').strip("'")))
    return conf


def save_conf(conf):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONF.write_text("".join(f'{k}="{v}"\n' for k, v in conf.items()))


def check_scheme(url):
    if not url.startswith(("https://", "http://")):
        raise ValueError("only http(s) URLs are supported")


def fetch(url, limit=MAX_PAGE_BYTES):
    check_scheme(url)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=10) as response:
        check_scheme(response.geturl())
        return response.headers.get("Content-Type", ""), response.read(limit + 1)


def duration_tool():
    if shutil.which("afinfo"):
        return "afinfo"
    if shutil.which("ffprobe"):
        return "ffprobe"
    return None


def duration(path):
    tool = duration_tool()
    try:
        if tool == "afinfo":
            output = subprocess.run(
                ["afinfo", str(path)], capture_output=True, text=True, timeout=5, check=False
            ).stdout
            match = re.search(r"estimated duration: ([0-9.]+)", output)
            return float(match.group(1)) if match else None
        if tool == "ffprobe":
            output = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout.strip()
            return float(output) if output else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def limits(category, conf):
    if category == "christmas":
        return (
            float(conf["CHRISTMAS_MIN_DURATION"]),
            float(conf["CHRISTMAS_MAX_DURATION"]),
            conf["CHRISTMAS_MAX_SECONDS"],
        )
    return float(conf["MIN_DURATION"]), float(conf["MAX_DURATION"]), conf["MAX_SECONDS"]


def in_range(seconds, category, conf):
    if seconds is None:
        return duration_tool() is None
    low, high, _ = limits(category, conf)
    return low <= seconds <= high


def valid_category(category):
    if category.startswith("search:"):
        return bool(category[len("search:") :].strip())
    return category in CATEGORIES + list(SPECIAL) + THEMES + ["any"]


def category_dir(category):
    return CACHE / re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")


def search_url(query, page):
    return "{}/en/search/?{}".format(BASE, urllib.parse.urlencode({"name": query, "page": page}))


def page_url(category, page, conf):
    if category == "christmas":
        queries = [q.strip() for q in conf["CHRISTMAS_QUERIES"].split(",") if q.strip()] or ["christmas"]
        return search_url(random.choice(queries), page)
    if category.startswith("search:"):
        return search_url(category[len("search:") :].strip(), page)
    path = SPECIAL.get(category) or "/en/categories/" + urllib.parse.quote(category) + "/"
    return f"{BASE}{path}?page={page}"


def meta_path(sound):
    return Path(str(sound) + ".json")


def remove_sound(sound):
    for path in (sound, meta_path(sound)):
        if path.exists():
            path.unlink()


def cached_seconds(sound):
    path = meta_path(sound)
    meta = json.loads(path.read_text()) if path.exists() else {"title": sound.stem}
    if meta.get("seconds") is None and duration_tool():
        meta["seconds"] = duration(sound)
        path.write_text(json.dumps(meta))
    return meta.get("seconds")


def parse_instants(text):
    found = re.findall(r"play\('(/media/sounds/[^']+\.mp3)'.*?title=\"Play (.*?) sound\"", text)
    return [(path, html.unescape(title)) for path, title in found]


def download_sound(path, target, title, category, conf):
    name = Path(path).name
    content_type, data = fetch(BASE + urllib.parse.quote(path), MAX_BYTES)
    if "audio" not in content_type or not data or len(data) > MAX_BYTES:
        return False
    partial = target / (name + ".part")
    partial.write_bytes(data)
    seconds = duration(partial)
    if not in_range(seconds, category, conf):
        partial.unlink()
        return False
    partial.rename(target / name)
    meta_path(target / name).write_text(json.dumps({"title": title, "source": BASE + path, "seconds": seconds}))
    return True


def refill(category, conf, count=3):
    target = category_dir(category)
    target.mkdir(parents=True, exist_ok=True)
    lock = target / ".lock"
    if lock.exists() and time.time() - lock.stat().st_mtime < 120:
        return 0
    lock.touch()
    added = 0
    max_page = 4 if category == "christmas" or category.startswith("search:") else int(conf["MAX_PAGE"])
    try:
        for attempt in range(4):
            page = 1 if attempt == 3 else random.randint(1, max(1, max_page))
            try:
                _, body = fetch(page_url(category, page, conf))
            except (urllib.error.URLError, OSError, ValueError):
                continue
            instants = parse_instants(body.decode("utf-8", "replace"))
            random.shuffle(instants)
            if category == "christmas":
                instants = [(p, t) for p, t in instants if CHRISTMAS_WORDS.search(t + " " + p)]
            for path, title in instants:
                if added >= count:
                    break
                if (target / Path(path).name).exists():
                    continue
                try:
                    if download_sound(path, target, title, category, conf):
                        added += 1
                except (urllib.error.URLError, OSError, ValueError):
                    continue
            if added >= count:
                break
        for sound in target.glob("*.mp3"):
            if not in_range(cached_seconds(sound), category, conf):
                remove_sound(sound)
        sounds = sorted(target.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        for old in sounds[: max(0, len(sounds) - int(conf["CACHE_SIZE"]))]:
            remove_sound(old)
    finally:
        if lock.exists():
            lock.unlink()
    return added


def usable_sounds(category, conf):
    return [s for s in category_dir(category).glob("*.mp3") if in_range(cached_seconds(s), category, conf)]


def pick_random(category, conf):
    target = category_dir(category)
    sounds = usable_sounds(category, conf)
    last = target / ".last"
    previous = last.read_text() if last.exists() else ""
    choices = [s for s in sounds if s.name != previous] or sounds
    if not choices:
        return None, None
    choice = random.choice(choices)
    last.write_text(choice.name)
    meta = meta_path(choice)
    title = json.loads(meta.read_text()).get("title") if meta.exists() else choice.stem
    return choice, title


def system_sound(name):
    for candidate in (MAC_SOUNDS / (name + ".aiff"), LINUX_SOUNDS / (name + ".oga"), LINUX_SOUNDS / (name + ".ogg")):
        if candidate.is_file():
            return candidate
    return None


def resolve_track(value):
    path = Path(os.path.expanduser(value))
    if path.is_file():
        return path
    return system_sound(value) or system_sound(DEFAULTS["DONE_SOUND"])


def player_command(sound, seconds, volume):
    if shutil.which("afplay"):
        return ["afplay", "-t", seconds, "-v", volume, str(sound)]
    factor = min(max(float(volume), 0.0), 1.0)
    level = str(int(factor * 100))
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet", "--length=" + seconds, "--volume=" + level, str(sound)]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", seconds, "-volume", level, str(sound)]
    if shutil.which("pw-play"):
        return ["pw-play", "--volume=" + str(factor), str(sound)]
    if shutil.which("paplay"):
        return ["paplay", "--volume=" + str(int(factor * 65536)), str(sound)]
    if shutil.which("mpg123") and str(sound).lower().endswith(".mp3"):
        return ["mpg123", "-q", "-f", str(int(factor * 32768)), str(sound)]
    return None


def spawn(args):
    return subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
    )


def alive(pid):
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def player_busy(pid_file):
    try:
        pid, until = pid_file.read_text().split()
        return time.time() < float(until) and alive(int(pid))
    except (OSError, ValueError):
        return False


def decode_command(sound, target):
    if shutil.which("afconvert"):
        return ["afconvert", "-f", "WAVE", "-d", f"LEI16@{ANALYSIS_RATE}", "-c", "1", str(sound), str(target)]
    if shutil.which("ffmpeg"):
        return ["ffmpeg", "-v", "error", "-y", "-i", str(sound), "-ac", "1", "-ar", str(ANALYSIS_RATE), str(target)]
    return None


def decode(sound, seconds, workdir):
    target = Path(workdir) / "decoded.wav"
    command = decode_command(sound, target)
    if not command:
        return None
    subprocess.run(command, capture_output=True, timeout=30, check=True)
    with wave.open(str(target)) as decoded:
        if decoded.getsampwidth() != 2 or decoded.getnchannels() != 1:
            return None
        rate = decoded.getframerate()
        samples = array.array("h", decoded.readframes(int(rate * float(seconds))))
    if sys.byteorder == "big":
        samples.byteswap()
    return samples, rate


def loudness(samples, rate):
    block = max(1, int(rate * BLOCK_SECONDS))
    energies = []
    peak = 0
    for start in range(0, len(samples), block):
        chunk = samples[start : start + block]
        if chunk:
            energies.append(sum(value * value for value in chunk) / len(chunk) / SAMPLE_FULL_SCALE**2)
            loudest = max(chunk)
            quietest = min(chunk)
            peak = max(peak, loudest, -quietest)
    loud = [e for e in energies if e > 10 ** (SILENCE_GATE_DB / 10)]
    if not loud:
        return None, peak / SAMPLE_FULL_SCALE
    mean = sum(loud) / len(loud)
    loud = [e for e in loud if e > mean * 10 ** (RELATIVE_GATE_DB / 10)]
    return 10 * math.log10(sum(loud) / len(loud)), peak / SAMPLE_FULL_SCALE


def gain_for(level, peak, conf):
    if level is None or peak <= 0:
        return 1.0
    wanted = 10 ** ((float(conf["TARGET_LEVEL"]) - level) / 20)
    return min(wanted, float(conf["MAX_BOOST"]), PEAK_CEILING / peak)


def normalized_copy(sound, seconds, conf, workdir):
    decoded = decode(sound, seconds, workdir)
    if not decoded:
        return None, None
    samples, rate = decoded
    level, peak = loudness(samples, rate)
    gain = gain_for(level, peak, conf) * min(max(float(conf["VOLUME"]), 0.0), 1.0)
    scaled = array.array("h", (max(-32768, min(32767, int(value * gain))) for value in samples))
    if sys.byteorder == "big":
        scaled.byteswap()
    target = Path(workdir) / "normalized.wav"
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(scaled.tobytes())
    return target, gain


def run_player(sound, seconds, conf):
    with tempfile.TemporaryDirectory(prefix=APP + "-") as workdir:
        command = None
        if conf.get("NORMALIZE") == "1":
            with contextlib.suppress(Exception):
                normalized, _ = normalized_copy(sound, seconds, conf, workdir)
                if normalized:
                    command = player_command(normalized, seconds, "1")
        command = command or player_command(sound, seconds, conf["VOLUME"])
        if not command:
            return
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            process.wait(timeout=float(seconds) + 0.5)
        except subprocess.TimeoutExpired:
            process.terminate()


def play_file(sound, seconds, conf):
    if not player_command(sound, seconds, conf["VOLUME"]):
        return False
    CACHE.mkdir(parents=True, exist_ok=True)
    pid_file = CACHE / ".player"
    with open(CACHE / ".player.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if player_busy(pid_file):
            return False
        process = spawn([sys.executable, os.path.abspath(__file__), "_play", seconds, str(sound)])
        pid_file.write_text(f"{process.pid} {time.time() + float(seconds) + 2}")
    return True


def notify(title, message):
    if shutil.which("osascript"):
        spawn(
            [
                "osascript",
                "-e",
                "on run argv",
                "-e",
                "display notification (item 1 of argv) with title (item 2 of argv)",
                "-e",
                "end run",
                message,
                title,
            ]
        )
    elif shutil.which("notify-send"):
        spawn(["notify-send", "--app-name=agent-notify-sound", title, message])


def duplicate(key, conf):
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / ".last-event", "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        previous = handle.read().split()
        now = time.time()
        if len(previous) == 2 and previous[0] == key and now - float(previous[1]) < float(conf["DEDUPE_SECONDS"]):
            return True
        handle.seek(0)
        handle.truncate()
        handle.write(f"{key} {now}")
    return False


def imported_by_devin(agent, payload):
    return agent == "claude" and "transcript_path" not in payload and bool(os.environ.get("DEVIN_PROJECT_DIR"))


def project_name(payload):
    for value in (
        payload.get("cwd"),
        os.environ.get("DEVIN_PROJECT_DIR"),
        os.environ.get("CLAUDE_PROJECT_DIR"),
        os.getcwd(),
    ):
        if value:
            return Path(value).name
    return ""


def effective_mode(is_input, conf):
    if conf["MODE"].lower() == "off":
        return "off"
    return (conf["INPUT_MODE"] if is_input and conf["INPUT_MODE"] else conf["MODE"]).lower()


def play(event, conf, agent="", payload=None):
    payload = payload or {}
    is_input = event == "input"
    mode = effective_mode(is_input, conf)
    key = "{}:{}".format(event, payload.get("session_id") or "-")
    if mode == "off" or imported_by_devin(agent, payload) or duplicate(key, conf):
        return None
    sound, title, played = None, None, False
    try:
        sound, title, played = choose_and_play(mode, is_input, conf)
    except Exception:
        played = False
    if conf.get("NOTIFY") == "1":
        with contextlib.suppress(Exception):
            message = "Needs your input or approval" if is_input else "Finished, check the session"
            if title and played:
                message += f" ({title})"
            name = AGENTS.get(agent, agent.capitalize() or "Agent")
            project = project_name(payload)
            notify(f"{name}: {project}" if project else name, message)
    return sound, title, played


def choose_and_play(mode, is_input, conf):
    sound, title, seconds = None, None, conf["MAX_SECONDS"]
    if mode in ("random", "christmas"):
        category = "christmas" if mode == "christmas" else conf["INPUT_CATEGORY" if is_input else "DONE_CATEGORY"]
        if category == "any":
            category = random.choice(CATEGORIES + list(SPECIAL))
        with contextlib.suppress(Exception):
            sound, title = pick_random(category, conf)
            if sound:
                seconds = limits(category, conf)[2]
        spawn([sys.executable, os.path.abspath(__file__), "refill", category])
    if sound is None:
        sound = resolve_track(conf["INPUT_SOUND" if is_input else "DONE_SOUND"])
    played = bool(sound) and play_file(sound, seconds, conf)
    return sound, title, played


def download_track(url):
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    if "/instant/" in url:
        _, body = fetch(url)
        match = re.search(r"/media/sounds/[^'\"]+\.mp3", body.decode("utf-8", "replace"))
        if not match:
            sys.exit("no sound found on " + url)
        url = BASE + match.group(0)
    content_type, data = fetch(url, MAX_BYTES)
    if "audio" not in content_type and not url.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".aiff")):
        sys.exit("not an audio file: " + url)
    if len(data) > MAX_BYTES:
        sys.exit("file is larger than 6 MB: " + url)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(urllib.parse.urlparse(url).path).name).strip(".-") or "sound.mp3"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    target = SOUNDS_DIR / f"{digest}-{name}"
    target.write_bytes(data)
    return str(target)


def track_value(value):
    if value.startswith(("http://", "https://")):
        return download_track(value)
    path = Path(os.path.expanduser(value))
    if path.is_file():
        return str(path.resolve())
    if system_sound(value):
        return value
    sys.exit("not a file, URL or system sound: " + value)


def read_payload():
    if sys.stdin.isatty():
        return {}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def print_status(conf):
    print("".join(f'{k}="{v}"\n' for k, v in conf.items()), end="")
    print(f"config: {CONF}")
    for category in list(SPECIAL) + CATEGORIES + THEMES:
        sounds = list(category_dir(category).glob("*.mp3"))
        if sounds:
            low, high, _ = limits(category, conf)
            print(
                f"cache {category}: {len(usable_sounds(category, conf))} of {len(sounds)} sounds in {low:g}-{high:g} s"
            )


def print_levels(rest, conf):
    if rest and Path(os.path.expanduser(rest[0])).is_file():
        sounds = [Path(os.path.expanduser(rest[0]))]
    else:
        category = " ".join(rest) or ("christmas" if conf["MODE"] == "christmas" else conf["DONE_CATEGORY"])
        sounds = sorted(category_dir(category).glob("*.mp3"))
    window = conf["CHRISTMAS_MAX_SECONDS"] if sounds and sounds[0].parent.name == "christmas" else conf["MAX_SECONDS"]
    if not sounds:
        print("no sounds to analyse")
        return
    print(f"target {conf['TARGET_LEVEL']} dB, max boost x{conf['MAX_BOOST']}")
    for sound in sounds:
        with tempfile.TemporaryDirectory(prefix=APP + "-") as workdir:
            decoded = decode(sound, window, workdir)
        if not decoded:
            print(f"{'?':>7}  {sound.name}  (no decoder: install ffmpeg on Linux)")
            continue
        level, peak = loudness(*decoded)
        gain = gain_for(level, peak, conf)
        shown = f"{level:6.1f}" if level is not None else "silent"
        print(f"{shown} dB  peak {peak:4.2f}  gain x{gain:4.2f}  {sound.name}")


def prefetch(categories, conf):
    for name in categories:
        if len(usable_sounds(name, conf)) < 3:
            refill(name, conf, 5)


def main(argv):
    args = argv or ["status"]
    command, rest = args[0], args[1:]
    conf = {} if command in ("done", "input", "_play") else load_conf()
    if command in ("done", "input"):
        agent = rest[rest.index("--agent") + 1] if "--agent" in rest and rest.index("--agent") + 1 < len(rest) else ""
        payload = read_payload()
        with contextlib.suppress(Exception):
            play(command, load_conf(), agent, payload)
        return 0
    if command == "_play":
        with contextlib.suppress(Exception):
            run_player(Path(rest[1]), rest[0], load_conf())
        return 0
    if command == "levels":
        print_levels(rest, conf)
        return 0
    if command == "refill":
        count = int(rest[-1]) if len(rest) > 1 and rest[-1].isdigit() else 3
        words = rest[:-1] if len(rest) > 1 and rest[-1].isdigit() else rest
        category = " ".join(words) or conf["DONE_CATEGORY"]
        if not valid_category(category) or category == "any":
            sys.exit(f"unknown category: {category}")
        added = refill(category, conf, count)
        if sys.stdout.isatty():
            print(f"added {added} sounds to {category}")
        return 0
    if command == "test":
        event = rest[0] if rest else "done"
        conf["DEDUPE_SECONDS"] = "0"
        result = play(event, conf, "test", {"cwd": os.getcwd()})
        if not result:
            print("muted")
        elif not result[0]:
            print("no sound file found, showed the notification only")
        elif not result[2] and not player_command(result[0], "1", "1"):
            print("no supported audio player found (macOS: afplay; Linux: mpv, ffplay, pw-play, paplay or mpg123)")
        elif not result[2]:
            print("another sound is still playing, showed the notification only")
        else:
            print("played {}{}".format(result[0], f" ({result[1]})" if result[1] else ""))
        return 0
    if command == "track":
        if not rest:
            sys.exit(USAGE)
        conf["MODE"] = "track"
        conf["DONE_SOUND"] = track_value(rest[0])
        if len(rest) > 1:
            conf["INPUT_SOUND"] = track_value(rest[1])
        save_conf(conf)
    elif command == "random":
        category = " ".join(rest) or "global"
        if category == "christmas":
            return main(["christmas"])
        if not valid_category(category):
            sys.exit(
                "unknown category: {}\nuse one of: {}, search:<words>".format(
                    category, ", ".join(list(SPECIAL) + CATEGORIES + ["any"])
                )
            )
        conf["MODE"] = "random"
        conf["DONE_CATEGORY"] = category
        conf["INPUT_CATEGORY"] = category
        save_conf(conf)
        prefetch((CATEGORIES + list(SPECIAL)) if category == "any" else [category], conf)
    elif command == "christmas":
        conf["MODE"] = "christmas"
        save_conf(conf)
        prefetch(["christmas"], conf)
    elif command == "set":
        if not rest:
            sys.exit(USAGE)
        key = rest[0].upper()
        if key not in DEFAULTS:
            sys.exit("unknown setting: {}\nsettings: {}".format(key, ", ".join(DEFAULTS)))
        value = " ".join(rest[1:])
        if key in ("MODE", "INPUT_MODE") and value and value not in MODES:
            sys.exit("{} must be one of: {}".format(key, ", ".join(MODES)))
        conf[key] = value
        save_conf(conf)
    elif command == "mute":
        if conf["MODE"] != "off":
            conf["PREVIOUS_MODE"] = conf["MODE"]
        conf["MODE"] = "off"
        save_conf(conf)
    elif command == "unmute":
        if conf["MODE"] == "off":
            conf["MODE"] = conf["PREVIOUS_MODE"] or "track"
            conf["PREVIOUS_MODE"] = ""
            save_conf(conf)
    elif command == "categories":
        print("\n".join(list(SPECIAL) + CATEGORIES + THEMES + ["any", "search:<words>"]))
        return 0
    elif command in ("version", "--version"):
        print(VERSION)
        return 0
    elif command != "status":
        print(USAGE, end="")
        return 2
    print_status(load_conf())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
