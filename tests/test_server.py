import importlib.util
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


if __name__ == "__main__":
    unittest.main()
