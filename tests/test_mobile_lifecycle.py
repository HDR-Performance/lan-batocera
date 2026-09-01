import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class MobileLifecycleTests(unittest.TestCase):
    def test_lifecycle_uses_reliable_mobile_background_events(self):
        script_path = os.path.join(REPOSITORY_ROOT, "web", "mobile-lifecycle.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()
        self.assertIn("visibilitychange", script)
        self.assertIn("visibilityState === 'hidden'", script)
        self.assertIn("freeze", script)
        self.assertIn("pagehide", script)
        self.assertIn("pageshow", script)
        self.assertIn("pause();", script)
        self.assertIn("Promise.resolve(save())", script)
        self.assertNotIn("unload", script)


if __name__ == "__main__":
    unittest.main()
