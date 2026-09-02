import io
import json
import os
import tempfile
import unittest
from unittest import mock

from src.update_manager import UpdateManager, version_tuple


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def release_response(version):
    return Response(json.dumps({
        "tag_name": f"v{version}",
        "name": f"LAN Batocera v{version}",
        "html_url": f"https://github.com/HDR-Performance/lan-batocera/releases/tag/v{version}",
    }).encode())


class UpdateManagerTests(unittest.TestCase):
    def test_semantic_versions_compare_numerically(self):
        self.assertGreater(version_tuple("1.10.0"), version_tuple("1.9.9"))
        with self.assertRaises(ValueError):
            version_tuple("latest")

    def test_check_reports_only_newer_stable_release(self):
        manager = UpdateManager("1.6.1")
        result = manager.check(lambda *_args, **_kwargs: release_response("1.7.0"))
        self.assertTrue(result["updateAvailable"])
        self.assertEqual(result["latestVersion"], "1.7.0")

    def test_start_validates_tagged_installer_and_launches_detached_runner(self):
        with tempfile.TemporaryDirectory() as root:
            status_path = os.path.join(root, "status.json")
            log_path = os.path.join(root, "logs", "update.log")
            manager = UpdateManager("1.6.1", status_path, root, log_path)
            responses = [
                release_response("1.7.0"),
                Response(b'#!/bin/sh\nLAN_BATOCERA_VERSION="1.7.0"\n'),
            ]
            opener = mock.Mock(side_effect=responses)
            launcher = mock.Mock()

            result = manager.start("1.7.0", opener, launcher)

            self.assertEqual(result["status"], "installing")
            self.assertEqual(result["targetVersion"], "1.7.0")
            launcher.assert_called_once()
            self.assertTrue(launcher.call_args.kwargs["start_new_session"])
            self.assertTrue(os.path.isfile(os.path.join(root, "lan-batocera-update-runner.sh")))

    def test_start_rejects_installer_with_wrong_embedded_version(self):
        with tempfile.TemporaryDirectory() as root:
            manager = UpdateManager("1.6.1", os.path.join(root, "status.json"), root,
                                    os.path.join(root, "logs", "update.log"))
            responses = [release_response("1.7.0"), Response(
                b'#!/bin/sh\nLAN_BATOCERA_VERSION="1.6.1"\n')]
            with self.assertRaises(RuntimeError):
                manager.start("1.7.0", mock.Mock(side_effect=responses), mock.Mock())


class UpdateUiTests(unittest.TestCase):
    def test_library_exposes_confirmed_github_update_flow(self):
        repository_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
        with open(os.path.join(repository_root, "web", "index.html"), encoding="utf-8") as page_file:
            page = page_file.read()
        self.assertIn("/api/update/check", page)
        self.assertIn("/api/update/install", page)
        self.assertIn("X-LAN-Batocera-Action':'install-update'", page)
        self.assertIn("updateDialog", page)


if __name__ == "__main__":
    unittest.main()
