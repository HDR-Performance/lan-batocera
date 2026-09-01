import os
import unittest


PLAY_PAGE = os.path.join(os.path.dirname(__file__), "..", "web", "play.html")


class PlayPageTests(unittest.TestCase):
    def test_auto_starts_and_offers_save_or_skip_exit(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("window.EJS_startOnLoaded=true", page)
        self.assertIn("Save State &amp; Exit", page)
        self.assertIn("Exit Without Saving", page)
        self.assertIn("window.EJS_emulator?.callEvent('exit')", page)

    def test_saved_state_manager_supports_load_and_multi_delete(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("Choose a saved state", page)
        self.assertIn('class="delete-choice" type="checkbox"', page)
        self.assertIn('class="load-choice" type="radio"', page)
        self.assertIn("/api/states/data", page)
        self.assertIn("method:'DELETE'", page)

    def test_native_hdmi_game_blocks_loader(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("/api/session-status", page)
        self.assertIn("status.nativeGameRunning", page)
        self.assertIn("Console in use", page)
        self.assertIn("document.createElement('script')", page)


if __name__ == "__main__":
    unittest.main()
