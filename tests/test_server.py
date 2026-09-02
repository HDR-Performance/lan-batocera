import importlib.util
import base64
import io
import json
import os
import tempfile
import unittest
import zipfile
from unittest import mock


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "server.py")
SPEC = importlib.util.spec_from_file_location("arcade_server", MODULE_PATH)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class ArcadeScannerTests(unittest.TestCase):
    def test_game_pages_and_roms_are_never_reused_from_browser_cache(self):
        self.assertEqual(server.cache_control_for_path("/play.html?launch=1"), "no-store, max-age=0")
        self.assertEqual(server.cache_control_for_path("/roms/snes/game.zip"), "no-store, max-age=0")
        self.assertEqual(server.cache_control_for_path("/"), "no-cache")

    def test_rom_byte_ranges_support_resume_and_suffix_requests(self):
        self.assertEqual(server.parse_byte_range("bytes=10-19", 100), (10, 19))
        self.assertEqual(server.parse_byte_range("bytes=90-", 100), (90, 99))
        self.assertEqual(server.parse_byte_range("bytes=-10", 100), (90, 99))
        with self.assertRaises(ValueError):
            server.parse_byte_range("bytes=100-120", 100)

    def test_rom_head_requests_use_the_same_metadata_handler_as_get(self):
        self.assertTrue(hasattr(server.Handler, "do_HEAD"))
        self.assertTrue(hasattr(server.Handler, "_serve_rom"))

    def test_project_version_is_semantic(self):
        self.assertRegex(server.project_version(), r"^\d+\.\d+\.\d+$")

    def test_scans_sega32x_zip_with_correct_emulatorjs_core(self):
        with tempfile.TemporaryDirectory() as roms:
            folder = os.path.join(roms, "sega32x")
            os.makedirs(folder)
            with open(os.path.join(folder, "Virtua Racing Deluxe.zip"), "wb") as output:
                output.write(b"fixture")
            previous_root = server.ROMS_ROOT
            server.ROMS_ROOT = roms
            try:
                games = server.games()
            finally:
                server.ROMS_ROOT = previous_root

        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["system"], "sega32x")
        self.assertEqual(games[0]["systemName"], "Sega 32X")
        self.assertEqual(games[0]["core"], "sega32x")
        self.assertEqual(games[0]["path"], "sega32x/Virtua Racing Deluxe.zip")
        self.assertRegex(games[0]["revision"], r"^\d+-\d+$")

    def test_sega32x_rar_is_not_advertised_as_directly_playable(self):
        extensions = server.SYSTEMS["sega32x"][3]
        self.assertIn(".zip", extensions)
        self.assertNotIn(".rar", extensions)

    def test_scans_batocera_c64_formats_with_emulatorjs_c64_core(self):
        with tempfile.TemporaryDirectory() as roms:
            folder = os.path.join(roms, "c64")
            os.makedirs(folder)
            for filename in ("Summer Games.tap", "Impossible Mission.d64"):
                with open(os.path.join(folder, filename), "wb") as output:
                    output.write(b"fixture")
            previous_root = server.ROMS_ROOT
            server.ROMS_ROOT = roms
            try:
                games = server.games()
            finally:
                server.ROMS_ROOT = previous_root

        self.assertEqual(len(games), 2)
        self.assertTrue(all(game["system"] == "c64" for game in games))
        self.assertTrue(all(game["systemName"] == "Commodore 64" for game in games))
        self.assertTrue(all(game["category"] == "Computer" for game in games))
        self.assertTrue(all(game["core"] == "c64" for game in games))

    def test_c64_supports_all_batocera_documented_formats(self):
        extensions = server.SYSTEMS["c64"][3]
        expected_extensions = {
            ".d64", ".d81", ".crt", ".prg", ".tap", ".t64", ".m3u", ".zip", ".7z"
        }
        self.assertEqual(extensions, expected_extensions)

    def test_scans_psx_cue_without_duplicate_bin_entry(self):
        with tempfile.TemporaryDirectory() as roms:
            folder = os.path.join(roms, "psx")
            os.makedirs(folder)
            for filename in ("Ridge Racer.cue", "Ridge Racer.bin", "Standalone.bin"):
                with open(os.path.join(folder, filename), "wb") as output:
                    output.write(b"fixture")
            previous_root = server.ROMS_ROOT
            server.ROMS_ROOT = roms
            try:
                games = server.games()
            finally:
                server.ROMS_ROOT = previous_root

        self.assertEqual([game["name"] for game in games], ["Ridge Racer", "Standalone"])
        self.assertTrue(all(game["core"] == "psx" for game in games))
        self.assertTrue(all(game["systemName"] == "Sony PlayStation" for game in games))

    def test_psx_supports_batocera_disc_formats(self):
        self.assertEqual(server.SYSTEMS["psx"][3], {
            ".bin", ".cue", ".img", ".mdf", ".pbp", ".toc", ".cbn", ".m3u",
            ".ccd", ".chd", ".iso"
        })


class SaveStateTests(unittest.TestCase):
    def test_exports_one_state_directly_and_multiple_states_as_portable_zip(self):
        original_root, original_native = server.STATE_ROOT, server.BATOCERA_SAVES_ROOT
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as native:
            server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = root, native
            try:
                game = "n64:n64/mario-kart-64.zip"
                first = server.save_state(game, "Race 1", base64.b64encode(b"state-one").decode())
                second = server.save_state(game, "Race 2", base64.b64encode(b"state-two").decode())
                content_type, filename, payload = server.export_states(game, [first["id"]])
                self.assertEqual(content_type, "application/octet-stream")
                self.assertTrue(filename.endswith(".state"))
                self.assertEqual(payload, b"state-one")
                content_type, filename, payload = server.export_states(
                    game, [first["id"], second["id"]])
                self.assertEqual(content_type, "application/zip")
                self.assertEqual(filename, "lan-batocera-save-states.zip")
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    manifest = json.loads(archive.read("lan-batocera-manifest.json"))
                    self.assertEqual(manifest["format"], "lan-batocera-states-v1")
                    self.assertEqual(len(manifest["states"]), 2)
                    self.assertEqual({archive.read(item["file"]) for item in manifest["states"]},
                                     {b"state-one", b"state-two"})
            finally:
                server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = original_root, original_native

    def test_every_lan_system_can_store_load_and_delete_browser_states(self):
        original_root, original_native = server.STATE_ROOT, server.BATOCERA_SAVES_ROOT
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as native:
            server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = root, native
            try:
                for system, (core, _name, _category, extensions) in server.SYSTEMS.items():
                    extension = sorted(extensions)[0]
                    game = f"{core}:{system}/save-test{extension}"
                    expected_state = f"state-{system}".encode()
                    saved = server.save_state(
                        game,
                        f"{system} state",
                        base64.b64encode(expected_state).decode(),
                    )
                    self.assertEqual(server.list_states(game)[0]["id"], saved["id"])
                    with open(server.state_file(game, saved["id"], ".state"), "rb") as source:
                        self.assertEqual(source.read(), expected_state)
                    self.assertEqual(server.delete_states(game, [saved["id"]]), 1)
                    self.assertEqual(server.list_states(game), [])
            finally:
                server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = original_root, original_native

    def test_save_list_native_mirror_load_and_multi_delete(self):
        original_root, original_native = server.STATE_ROOT, server.BATOCERA_SAVES_ROOT
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as native:
            server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = root, native
            try:
                first = server.save_state("snes:snes/game.zip", "First", base64.b64encode(b"state-one").decode())
                second = server.save_state("snes:snes/game.zip", "Second", base64.b64encode(b"state-two").decode())
                states = server.list_states("snes:snes/game.zip")
                self.assertEqual({item["id"] for item in states}, {first["id"], second["id"]})
                self.assertEqual({first["nativeSlot"], second["nativeSlot"]}, {0, 1})
                self.assertTrue(os.path.isfile(os.path.join(native, first["nativePath"])))
                with open(server.state_file("snes:snes/game.zip", first["id"], ".state"), "rb") as source:
                    self.assertEqual(source.read(), b"state-one")
                self.assertEqual(server.delete_states("snes:snes/game.zip", [first["id"], second["id"]]), 2)
                self.assertEqual(server.list_states("snes:snes/game.zip"), [])
                self.assertFalse(os.path.exists(os.path.join(native, first["nativePath"])))
            finally:
                server.STATE_ROOT, server.BATOCERA_SAVES_ROOT = original_root, original_native

    def test_detects_native_emulator_process(self):
        with tempfile.TemporaryDirectory() as proc:
            os.mkdir(os.path.join(proc, "123"))
            with open(os.path.join(proc, "123", "cmdline"), "wb") as output:
                output.write(b"/usr/bin/retroarch\0-L\0snes9x_libretro.so")
            self.assertTrue(server.native_game_running(proc))

    def test_stop_uses_batocera_supported_emulator_kill(self):
        statuses = [{"nativeGameRunning": True}, {"nativeGameRunning": False}]
        completed = mock.Mock(returncode=20)
        with mock.patch.object(server, "native_game_status", side_effect=statuses), \
                mock.patch.object(server.subprocess, "run", return_value=completed) as run:
            result = server.stop_native_game()
        self.assertTrue(result["stopped"])
        run.assert_called_once_with(
            ["/usr/bin/batocera-es-swissknife", "--emukill", "8"],
            capture_output=True, text=True, timeout=15, check=False)


if __name__ == "__main__":
    unittest.main()
