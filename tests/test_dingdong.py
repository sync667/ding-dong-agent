import array
import importlib
import json
import math
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_module(name, home):
    env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache")}
    with mock.patch.dict(os.environ, env):
        with mock.patch("pathlib.Path.home", return_value=home):
            if name in sys.modules:
                del sys.modules[name]
            return importlib.import_module(name)


INSTANT_HTML = (
    "<button class=\"small-button\" onclick=\"play('/media/sounds/anime-wow.mp3', 'loader-1', 'anime-wow-1')\" "
    'title="Play Anime &amp; Wow sound" type="button"></button>\n'
    "<button class=\"small-button\" onclick=\"play('/media/sounds/bruh.mp3', 'loader-2', 'bruh-2')\" "
    'title="Play Bruh sound" type="button"></button>\n'
)


class NotifySoundTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.ns = load_module("dingdong", self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_round_trip_keeps_defaults(self):
        conf = self.ns.load_conf()
        conf["MODE"] = "random"
        conf["DONE_CATEGORY"] = "anime & manga"
        self.ns.save_conf(conf)
        loaded = self.ns.load_conf()
        self.assertEqual(loaded["MODE"], "random")
        self.assertEqual(loaded["DONE_CATEGORY"], "anime & manga")
        self.assertEqual(loaded["MIN_DURATION"], "3")

    def test_duration_range(self):
        conf = self.ns.load_conf()
        with mock.patch.object(self.ns, "duration_tool", return_value="afinfo"):
            self.assertTrue(self.ns.in_range(3.0, "memes", conf))
            self.assertTrue(self.ns.in_range(10.0, "memes", conf))
            self.assertFalse(self.ns.in_range(2.9, "memes", conf))
            self.assertFalse(self.ns.in_range(10.1, "memes", conf))
            self.assertFalse(self.ns.in_range(None, "memes", conf))
            self.assertTrue(self.ns.in_range(180.0, "christmas", conf))
            self.assertFalse(self.ns.in_range(1.0, "christmas", conf))
        with mock.patch.object(self.ns, "duration_tool", return_value=None):
            self.assertTrue(self.ns.in_range(None, "memes", conf))

    def test_christmas_uses_search_and_caps_playback_at_15_seconds(self):
        conf = self.ns.load_conf()
        conf["CHRISTMAS_QUERIES"] = "jingle bells"
        self.assertEqual(
            self.ns.page_url("christmas", 2, conf), "https://www.myinstants.com/en/search/?name=jingle+bells&page=2"
        )
        self.assertEqual(self.ns.limits("christmas", conf), (2.0, 300.0, "15"))
        self.assertEqual(
            self.ns.page_url("anime & manga", 3, conf),
            "https://www.myinstants.com/en/categories/anime%20%26%20manga/?page=3",
        )
        self.assertEqual(
            self.ns.page_url("search:air horn", 1, conf), "https://www.myinstants.com/en/search/?name=air+horn&page=1"
        )

    def test_valid_categories(self):
        for category in ("global", "trending", "memes", "christmas", "any", "search:bruh"):
            self.assertTrue(self.ns.valid_category(category), category)
        for category in ("nope", "search:", "search:  "):
            self.assertFalse(self.ns.valid_category(category), category)

    def test_second_session_only_notifies_while_a_sound_plays(self):
        conf = self.ns.load_conf()
        sound = self.home / "wow.mp3"
        sound.write_bytes(b"x")
        process = mock.Mock(pid=os.getpid())
        with mock.patch.object(self.ns, "player_command", return_value=["afplay", str(sound)]), mock.patch.object(
            self.ns, "spawn", return_value=process
        ) as spawn:
            self.assertTrue(self.ns.play_file(sound, "10", conf))
            self.assertFalse(self.ns.play_file(sound, "10", conf))
        self.assertEqual(spawn.call_count, 1)
        (self.ns.CACHE / ".player").write_text(f"{os.getpid()} {0}")
        with mock.patch.object(self.ns, "player_command", return_value=["afplay", str(sound)]), mock.patch.object(
            self.ns, "spawn", return_value=process
        ):
            self.assertTrue(self.ns.play_file(sound, "10", conf))

    def test_parse_instants_unescapes_titles(self):
        self.assertEqual(
            self.ns.parse_instants(INSTANT_HTML),
            [("/media/sounds/anime-wow.mp3", "Anime & Wow"), ("/media/sounds/bruh.mp3", "Bruh")],
        )

    def test_duplicate_events_are_skipped_within_window(self):
        conf = self.ns.load_conf()
        self.assertFalse(self.ns.duplicate("done:a", conf))
        self.assertTrue(self.ns.duplicate("done:a", conf))
        self.assertFalse(self.ns.duplicate("done:b", conf))
        self.assertFalse(self.ns.duplicate("input:b", conf))
        conf["DEDUPE_SECONDS"] = "0"
        self.assertFalse(self.ns.duplicate("input:b", conf))

    def test_claude_hooks_imported_by_devin_are_skipped(self):
        with mock.patch.dict(os.environ, {"DEVIN_PROJECT_DIR": "/tmp/x"}):
            self.assertTrue(self.ns.imported_by_devin("claude", {"session_id": "1"}))
            self.assertFalse(self.ns.imported_by_devin("claude", {"transcript_path": "/t"}))
            self.assertFalse(self.ns.imported_by_devin("devin", {}))
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEVIN_PROJECT_DIR", None)
            self.assertFalse(self.ns.imported_by_devin("claude", {}))

    def test_track_mode_plays_configured_file_and_notifies(self):
        sound = self.home / "wow.mp3"
        sound.write_bytes(b"x")
        conf = self.ns.load_conf()
        conf["DONE_SOUND"] = str(sound)
        with mock.patch.object(self.ns, "play_file", return_value=True) as play_file, mock.patch.object(
            self.ns, "notify"
        ) as notify:
            self.ns.play("done", conf, "codex", {"cwd": "/work/my-repo"})
        play_file.assert_called_once_with(sound, "10", conf)
        notify.assert_called_once_with("Codex: my-repo", "Finished, check the session")

    def test_busy_player_still_notifies_without_sound_title(self):
        conf = self.ns.load_conf()
        conf["MODE"] = "christmas"
        target = self.ns.category_dir("christmas")
        target.mkdir(parents=True)
        (target / "jingle.mp3").write_bytes(b"x")
        (target / "jingle.mp3.json").write_text(json.dumps({"title": "Jingle", "seconds": 40.0}))
        with mock.patch.object(self.ns, "duration_tool", return_value="afinfo"), mock.patch.object(
            self.ns, "spawn"
        ), mock.patch.object(self.ns, "play_file", return_value=False) as play_file, mock.patch.object(
            self.ns, "notify"
        ) as notify:
            sound, title, played = self.ns.play("done", conf, "devin", {"cwd": "/w/other", "session_id": "2"})
        self.assertEqual((sound.name, title, played), ("jingle.mp3", "Jingle", False))
        play_file.assert_called_once_with(target / "jingle.mp3", "15", conf)
        notify.assert_called_once_with("Devin: other", "Finished, check the session")

    def test_mute_also_silences_input_mode_override(self):
        conf = self.ns.load_conf()
        conf["MODE"] = "off"
        conf["INPUT_MODE"] = "track"
        self.assertEqual(self.ns.effective_mode(True, conf), "off")
        conf["MODE"] = "christmas"
        self.assertEqual(self.ns.effective_mode(True, conf), "track")
        self.assertEqual(self.ns.effective_mode(False, conf), "christmas")

    def test_fetch_rejects_non_http_schemes(self):
        for url in ("file:///etc/passwd", "ftp://example.com/a.mp3"):
            with self.assertRaises(ValueError):
                self.ns.fetch(url)

    def test_hook_entry_never_fails_on_broken_config(self):
        self.ns.CONFIG_DIR.mkdir(parents=True)
        self.ns.CONF.write_bytes(b"\xff\xfe broken")
        with mock.patch.object(self.ns, "read_payload", return_value={}):
            self.assertEqual(self.ns.main(["done", "--agent", "devin"]), 0)

    def test_notification_survives_a_failing_player(self):
        conf = self.ns.load_conf()
        with mock.patch.object(self.ns, "play_file", side_effect=OSError("boom")), mock.patch.object(
            self.ns, "notify"
        ) as notify:
            self.assertEqual(self.ns.play("done", conf, "claude", {"transcript_path": "/t", "cwd": "/w/r"})[2], False)
        notify.assert_called_once_with("Claude: r", "Finished, check the session")

    def test_off_mode_is_silent(self):
        conf = self.ns.load_conf()
        conf["MODE"] = "off"
        with mock.patch.object(self.ns, "play_file") as play_file, mock.patch.object(self.ns, "notify") as notify:
            self.assertIsNone(self.ns.play("done", conf, "devin", {}))
        play_file.assert_not_called()
        notify.assert_not_called()

    def test_random_mode_picks_cached_sound_in_range(self):
        conf = self.ns.load_conf()
        conf["MODE"] = "random"
        conf["DONE_CATEGORY"] = "memes"
        target = self.ns.category_dir("memes")
        target.mkdir(parents=True)
        for name, seconds in (("short.mp3", 1.0), ("good.mp3", 5.0), ("long.mp3", 30.0)):
            (target / name).write_bytes(b"x")
            (target / (name + ".json")).write_text(json.dumps({"title": name, "seconds": seconds}))
        with mock.patch.object(self.ns, "duration_tool", return_value="afinfo"), mock.patch.object(
            self.ns, "spawn"
        ), mock.patch.object(self.ns, "play_file", return_value=True) as play_file, mock.patch.object(
            self.ns, "notify"
        ):
            sound, title, _ = self.ns.play("done", conf, "claude", {"transcript_path": "/t"})
        self.assertEqual(sound.name, "good.mp3")
        self.assertEqual(title, "good.mp3")
        play_file.assert_called_once()


class LoudnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.ns = load_module("dingdong", self.home)
        self.conf = self.ns.load_conf()

    def tearDown(self):
        self.tmp.cleanup()

    def tone(self, amplitude, seconds=1.0, rate=8000):
        count = int(rate * seconds)
        return array.array("h", (int(amplitude * 32767 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(count)))

    def test_loudness_of_a_sine_wave(self):
        level, peak = self.ns.loudness(self.tone(0.5), 8000)
        self.assertAlmostEqual(level, 20 * math.log10(0.5 / math.sqrt(2)), places=1)
        self.assertAlmostEqual(peak, 0.5, places=2)

    def test_silence_is_left_alone(self):
        level, _ = self.ns.loudness(array.array("h", [0] * 8000), 8000)
        self.assertIsNone(level)
        self.assertEqual(self.ns.gain_for(None, 0.0, self.conf), 1.0)

    def test_gain_evens_out_levels_without_clipping(self):
        self.conf["TARGET_LEVEL"] = "-20"
        self.assertAlmostEqual(self.ns.gain_for(-10.0, 0.5, self.conf), 10 ** (-10 / 20), places=4)
        self.assertEqual(self.ns.gain_for(-40.0, 0.01, self.conf), 4.0)
        self.assertAlmostEqual(self.ns.gain_for(-30.0, 0.5, self.conf), 0.97 / 0.5, places=4)

    def test_normalized_copy_lands_on_the_target_level(self):
        self.conf["TARGET_LEVEL"] = "-20"
        for amplitude in (0.05, 0.8):
            with tempfile.TemporaryDirectory() as workdir, mock.patch.object(
                self.ns, "decode", return_value=(self.tone(amplitude), 8000)
            ):
                target, _ = self.ns.normalized_copy(Path("x.mp3"), "1", self.conf, workdir)
                with wave.open(str(target)) as result:
                    samples = array.array("h", result.readframes(result.getnframes()))
            level, peak = self.ns.loudness(samples, 8000)
            self.assertAlmostEqual(level, -20.0, delta=0.2)
            self.assertLessEqual(peak, 0.98)

    def test_player_falls_back_to_the_original_file_when_decoding_fails(self):
        sound = self.home / "a.mp3"
        sound.write_bytes(b"x")
        process = mock.Mock()
        with mock.patch.object(self.ns, "decode", side_effect=OSError("no decoder")), mock.patch.object(
            self.ns, "player_command", return_value=["afplay", str(sound)]
        ) as command, mock.patch("subprocess.Popen", return_value=process):
            self.ns.run_player(sound, "5", self.conf)
        command.assert_called_once_with(sound, "5", self.conf["VOLUME"])
        process.wait.assert_called_once()


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.installer = load_module("installer", self.home)
        self.targets = self.installer.agent_targets(self.home, env={})
        quiet = mock.patch("builtins.print")
        quiet.start()
        self.addCleanup(quiet.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_is_idempotent_and_keeps_foreign_hooks(self):
        settings = self.targets["claude"]["settings"]
        settings.parent.mkdir(parents=True)
        foreign = [
            {"type": "command", "command": "other-tool"},
            {"type": "command", "command": "~/bin/my-notify-sound.sh"},
            {"type": "command", "command": "terminal-notifier -message done # notify_sound legacy"},
        ]
        odd = {"enabled": True}
        settings.write_text(json.dumps({"theme": "dark", "hooks": {"Stop": [{"hooks": foreign}], "Odd": odd}}))
        for _ in range(2):
            self.installer.configure_hooks(self.targets["claude"], "/bin/dingdong", "claude", False, False)
        data = json.loads(settings.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["hooks"]["Odd"], odd)
        stop_commands = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_commands, [h["command"] for h in foreign] + ['"/bin/dingdong" done --agent claude'])
        self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "^AskUserQuestion$")
        self.installer.configure_hooks(self.targets["claude"], "/bin/dingdong", "claude", True, False)
        data = json.loads(settings.read_text())
        self.assertEqual(data["hooks"], {"Stop": [{"hooks": foreign}], "Odd": odd})

    def test_old_agent_notify_sound_hooks_are_replaced(self):
        settings = self.targets["devin"]["settings"]
        settings.parent.mkdir(parents=True)
        old = {"type": "command", "command": '"/h/.local/bin/notify-sound" done --agent devin', "timeout": 10}
        settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [old]}]}}))
        self.installer.configure_hooks(self.targets["devin"], "/bin/dingdong", "devin", False, False)
        data = json.loads(settings.read_text())
        self.assertEqual(
            [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]], ['"/bin/dingdong" done --agent devin']
        )

    def test_backups_never_overwrite_each_other(self):
        path = self.home / "settings.json"
        path.write_text("{}")
        first = self.installer.backup(path)
        second = self.installer.backup(path)
        self.assertNotEqual(first, second)
        self.assertTrue(first.exists() and second.exists())

    def test_codex_home_comes_from_the_given_environment(self):
        targets = self.installer.agent_targets(self.home, env={"CODEX_HOME": str(self.home / "cx")})
        self.assertEqual(targets["codex"]["settings"], self.home / "cx" / "hooks.json")

    def test_skill_folder_not_created_by_us_is_left_alone(self):
        skills = self.home / "skills"
        (skills / "ding-dong").mkdir(parents=True)
        (skills / "ding-dong" / "SKILL.md").write_text("mine")
        self.installer.install_skill(skills, False, False, False)
        self.assertEqual((skills / "ding-dong" / "SKILL.md").read_text(), "mine")
        self.installer.install_skill(skills, False, False, True)
        self.assertTrue((skills / "ding-dong" / ".installed-by-ding-dong-agent").exists())

    def test_codex_hooks_file_is_created_without_matcher_for_stop(self):
        self.installer.configure_hooks(self.targets["codex"], "/bin/dingdong", "codex", False, False)
        data = json.loads(self.targets["codex"]["settings"].read_text())
        self.assertEqual(
            data["hooks"]["Stop"],
            [{"hooks": [{"type": "command", "command": '"/bin/dingdong" done --agent codex', "timeout": 10}]}],
        )
        self.assertIn("PermissionRequest", data["hooks"])


if __name__ == "__main__":
    unittest.main()
