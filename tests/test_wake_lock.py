import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class WakeLockTests(unittest.TestCase):
    def test_wake_lock_has_native_fallback_and_release_paths(self):
        script_path = os.path.join(REPOSITORY_ROOT, "web", "wake-lock.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()
        self.assertIn("navigator.wakeLock.request('screen')", script)
        self.assertIn("window.isSecureContext", script)
        self.assertIn("new window.NoSleep()", script)
        self.assertIn("nativeLock.release()", script)
        self.assertIn("fallbackLock?.disable?.()", script)
        self.assertIn("aria-pressed", script)


if __name__ == "__main__":
    unittest.main()
