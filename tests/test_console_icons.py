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

    def test_primary_navigation_keeps_updates_in_header_and_tools_grouped(self):
        header_start = self.index.index('<header class="page-header">')
        navigation_start = self.index.index('<nav class="views"')
        navigation_end = self.index.index('</nav>', navigation_start)
        self.assertLess(header_start, navigation_start)
        self.assertLess(self.index.index('id="updateOpen"'), navigation_start)
        navigation = self.index[navigation_start:navigation_end]
        self.assertIn('<details class="tools-menu">', navigation)
        self.assertEqual(navigation.count('<button class="view'), 3)
        self.assertNotIn('id="updateOpen"', navigation)


if __name__ == "__main__":
    unittest.main()
