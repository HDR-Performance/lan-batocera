import importlib.util
import base64
import os
import tempfile
import unittest


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "server.py")
SPEC = importlib.util.spec_from_file_location("arcade_server", MODULE_PATH)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class ArcadeScannerTests(unittest.TestCase):
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

    def test_sega32x_rar_is_not_advertised_as_directly_playable(self):
        extensions = server.SYSTEMS["sega32x"][3]
        self.assertIn(".zip", extensions)
        self.assertNotIn(".rar", extensions)


class SaveStateTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
