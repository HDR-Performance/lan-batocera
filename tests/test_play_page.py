import os
import unittest


PLAY_PAGE = os.path.join(os.path.dirname(__file__), "..", "web", "play.html")


class PlayPageTests(unittest.TestCase):
    def test_uses_interactive_start_instead_of_unreliable_auto_boot(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("window.EJS_startOnLoaded=false", page)
        self.assertIn("window.EJS_startButtonName='Start '+name", page)
        self.assertNotIn("window.EJS_startOnLoaded=true", page)


if __name__ == "__main__":
    unittest.main()
