import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class FullscreenControlTests(unittest.TestCase):
    def test_control_handles_standard_mobile_and_fallback_paths(self):
        script_path = os.path.join(REPOSITORY_ROOT, "web", "fullscreen-controls.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()
        self.assertIn("requestFullscreen", script)
        self.assertIn("webkitRequestFullscreen", script)
        self.assertIn("webkitRequestFullScreen", script)
        self.assertIn("exitFullscreen", script)
        self.assertIn("webkitExitFullscreen", script)
        self.assertIn("webkitCancelFullScreen", script)
        self.assertIn("fullscreenchange", script)
        self.assertIn("webkitfullscreenchange", script)
        self.assertIn("Add to Home Screen", script)


if __name__ == "__main__":
    unittest.main()
