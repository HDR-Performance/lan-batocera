import os
import re
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
SEMANTIC_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ReleaseVersionTests(unittest.TestCase):
    def test_version_file_contains_semantic_version(self):
        with open(os.path.join(REPOSITORY_ROOT, "VERSION"), encoding="utf-8") as version_file:
            version = version_file.read().strip()
        self.assertRegex(version, SEMANTIC_VERSION_PATTERN)

    def test_installer_copies_and_reports_version(self):
        with open(os.path.join(REPOSITORY_ROOT, "install.sh"), encoding="utf-8") as installer_file:
            installer = installer_file.read()
        self.assertIn('install -m 0644 "$APP_ROOT/VERSION" "$ARCADE_ROOT/VERSION"', installer)
        self.assertIn('install -m 0644 "$APP_ROOT/web/controller-presets.js"', installer)
        self.assertIn('install -m 0644 "$APP_ROOT/web/themes.js"', installer)
        self.assertIn('LAN Batocera version:', installer)

    def test_standalone_installer_matches_release_version(self):
        with open(os.path.join(REPOSITORY_ROOT, "VERSION"), encoding="utf-8") as version_file:
            version = version_file.read().strip()
        with open(os.path.join(REPOSITORY_ROOT, "standalone-install.sh"), encoding="utf-8") as installer_file:
            installer = installer_file.read()
        self.assertIn(f'LAN_BATOCERA_VERSION="{version}"', installer)
        self.assertIn("requires an existing Batocera installation", installer)
        self.assertIn("archive/refs/tags/v${LAN_BATOCERA_VERSION}.tar.gz", installer)

    def test_readme_distinguishes_default_credentials(self):
        with open(os.path.join(REPOSITORY_ROOT, "README.md"), encoding="utf-8") as readme_file:
            readme = readme_file.read()
        self.assertIn("Batocera SSH", readme)
        self.assertIn("`root` | `linux`", readme)
        self.assertIn("LAN Batocera web file manager", readme)
        self.assertIn("`Batocera` | `Batocera`", readme)
        self.assertIn("Batocera Windows/SMB share", readme)
        self.assertIn("Enforce Security", readme)


if __name__ == "__main__":
    unittest.main()
