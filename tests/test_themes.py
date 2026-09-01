import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class ThemeTests(unittest.TestCase):
    def read_file(self, relative_path):
        with open(os.path.join(REPOSITORY_ROOT, relative_path), encoding="utf-8") as source_file:
            return source_file.read()

    def test_builtin_themes_and_custom_validation_exist(self):
        themes = self.read_file("web/themes.js")
        self.assertIn("Neon Arcade", themes)
        self.assertIn("Classic Dark", themes)
        self.assertIn("Pixel Purple", themes)
        self.assertIn("COLOR_PATTERN", themes)
        self.assertIn("COLOR_PROPERTIES", themes)

    def test_library_loads_theme_before_rendering(self):
        library_page = self.read_file("web/index.html")
        theme_script_position = library_page.index('/themes.js')
        body_position = library_page.index('<body>')
        self.assertLess(theme_script_position, body_position)
        self.assertIn("Save My Theme", library_page)
        self.assertIn("themeDialog", library_page)


if __name__ == "__main__":
    unittest.main()
