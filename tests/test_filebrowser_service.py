import os
import unittest


SERVICE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "services", "filebrowser_quantum"
)


class FileBrowserServiceTests(unittest.TestCase):
    def test_restart_waits_for_backend_shutdown(self):
        with open(SERVICE_PATH, encoding="utf-8") as source:
            service = source.read()

        self.assertIn("SHUTDOWN_TIMEOUT_SECONDS=60", service)
        self.assertIn('while kill -0 "$pid"', service)
        self.assertIn('stop_process "$PROXYPID"', service)
        self.assertIn('stop_process "$PIDFILE"', service)
        self.assertIn('restart) "$0" stop && "$0" start', service)


if __name__ == "__main__":
    unittest.main()
