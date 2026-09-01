import os
import unittest


ROOT = os.path.join(os.path.dirname(__file__), "..")


class MdnsServiceTests(unittest.TestCase):
    def test_installer_publishes_rom_manager_alias(self):
        with open(os.path.join(ROOT, "services", "lan_batocera_mdns"), encoding="utf-8") as source:
            service = source.read()
        with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as source:
            installer = source.read()
        self.assertIn("BatoceraRoms.local", service)
        self.assertIn("avahi-publish-address -R", service)
        self.assertIn("enable lan_batocera_mdns", installer)
        self.assertIn("batoceraroms.local:8081", installer)


if __name__ == "__main__":
    unittest.main()
