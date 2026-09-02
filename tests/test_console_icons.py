import os
import unittest


INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")


class ConsoleIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX_PATH, "r", encoding="utf-8") as source:
            cls.index = source.read()

    def test_supported_console_icons_are_bundled_locally(self):
        for system in ("atari2600", "nes", "snes", "n64", "megadrive", "sega32x", "gba", "c64"):
            self.assertIn(system + ":ICON(", self.index)
        self.assertNotIn("<img class=\"console-icon\"", self.index)

    def test_console_cards_render_icon_and_accessible_label(self):
        self.assertIn("CONSOLE_ICONS[data.system]||fallbackConsoleIcon", self.index)
        self.assertIn("button.setAttribute('aria-label'", self.index)
        self.assertIn('class="console-icon" aria-hidden="true"', self.index)

    def test_all_and_console_views_have_touch_friendly_alphabet_filter(self):
        self.assertIn('id="alphabet"', self.index)
        self.assertIn("...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'", self.index)
        self.assertIn("firstGroup(game.name)===activeLetter", self.index)
        self.assertIn("view!=='all'", self.index)


if __name__ == "__main__":
    unittest.main()
