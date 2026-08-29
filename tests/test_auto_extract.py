import importlib.util
import gzip
import os
import tempfile
import unittest
import zipfile


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "upload_proxy.py")
SPEC = importlib.util.spec_from_file_location("upload_proxy", MODULE_PATH)
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)


def make_zip(path, files):
    with zipfile.ZipFile(path, "w") as package:
        for name, content in files.items():
            package.writestr(name, content)


class AutoExtractTests(unittest.TestCase):
    def test_filebrowser_frontend_gains_real_type_sort_control(self):
        fixture = b"|".join(old for old, _new in proxy.FILE_TYPE_JS_PATCHES)
        patched, changed = proxy._patch_file_type_sort(
            "/public/static/assets/index-test.js", fixture)
        self.assertTrue(changed)
        self.assertIn(b'typeSorted(){return be.sorting().by==="type"}', patched)
        self.assertIn(b'r.sort("type")', patched)
        self.assertIn(b"Sort by file type", patched)

    def test_unrecognized_frontend_asset_is_not_modified(self):
        original = b"console.log('different version')"
        patched, changed = proxy._patch_file_type_sort(
            "/public/static/assets/index-other.js", original)
        self.assertFalse(changed)
        self.assertIs(patched, original)

    def test_file_type_patch_fixture_survives_gzip_delivery(self):
        fixture = b"|".join(old for old, _new in proxy.FILE_TYPE_JS_PATCHES)
        decoded = gzip.decompress(gzip.compress(fixture))
        patched, changed = proxy._patch_file_type_sort(
            "/public/static/assets/index-compressed.js", decoded)
        self.assertTrue(changed)
        self.assertIn(b"Sort by file type", patched)

    def test_filebrowser_html_versions_the_patched_frontend_asset(self):
        html = b'<script type="module" src="/public/static/assets/index-test.js"></script>'
        versioned, changed = proxy._version_filebrowser_html(html)
        self.assertTrue(changed)
        self.assertIn(b'index-test.js?lan-batocera-type-sort=1"', versioned)

    def test_current_file_manager_directory_becomes_auto_extract_context(self):
        context = proxy._directory_from_referer(
            "http://192.168.0.148:8081/files/Games/sega32x/My%20Folder/")
        self.assertEqual(context, {"source": "Games", "directory": "sega32x/My Folder"})
        page = proxy._tools_page_for_context(
            "http://192.168.0.148:8081/files/Games/sega32x/")
        self.assertIn(b'autoDirectory.value="sega32x"', page)
        self.assertIn(b"autoSubmit.click()", page)

    def test_unknown_referer_keeps_manual_archive_tools(self):
        self.assertIs(proxy._tools_page_for_context("http://example.test/"), proxy.TOOLS_PAGE)

    def test_parses_and_validates_rar_listing(self):
        listing = """7-Zip\n----------
Path = Game/Game.bin
Folder = -
Size = 12
Encrypted = -
Split Before = -
Split After = -

Path = Game
Folder = +
Size = 0
Encrypted = -
Split Before = -
Split After = -
"""
        records, size = proxy._parse_7z_listing(listing)
        self.assertEqual(len(records), 2)
        self.assertEqual(size, 12)

    def test_rejects_unsafe_or_encrypted_rar_listing(self):
        unsafe = """7-Zip\n----------
Path = ../escape.bin
Folder = -
Size = 1
Encrypted = -
"""
        encrypted = """7-Zip\n----------
Path = game.bin
Folder = -
Size = 1
Encrypted = +
"""
        with self.assertRaisesRegex(ValueError, "unsafe path"):
            proxy._parse_7z_listing(unsafe)
        with self.assertRaisesRegex(ValueError, "Password-protected"):
            proxy._parse_7z_listing(encrypted)

    def test_extracts_beside_archive_and_deletes_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = os.path.join(directory, "game.zip")
            make_zip(archive, {"game.rom": b"rom data", "art/cover.txt": b"cover"})

            files, size = proxy._extract_zip_beside_archive(archive)

            self.assertEqual(files, 2)
            self.assertEqual(size, 13)
            self.assertFalse(os.path.exists(archive))
            self.assertTrue(os.path.isfile(os.path.join(directory, "game.rom")))
            self.assertTrue(os.path.isfile(os.path.join(directory, "art", "cover.txt")))

    def test_collision_keeps_archive_and_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = os.path.join(directory, "game.zip")
            existing = os.path.join(directory, "game.rom")
            make_zip(archive, {"game.rom": b"new"})
            with open(existing, "wb") as output:
                output.write(b"existing")

            with self.assertRaisesRegex(ValueError, "Output already exists"):
                proxy._extract_zip_beside_archive(archive)

            self.assertTrue(os.path.isfile(archive))
            with open(existing, "rb") as source:
                self.assertEqual(source.read(), b"existing")

    def test_unsafe_path_keeps_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = os.path.join(directory, "unsafe.zip")
            make_zip(archive, {"../escape.rom": b"no"})

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                proxy._extract_zip_beside_archive(archive)

            self.assertTrue(os.path.isfile(archive))
            self.assertFalse(os.path.exists(os.path.join(directory, "..", "escape.rom")))

    def test_batch_processes_archives_sequentially_and_reports_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            make_zip(os.path.join(directory, "a.zip"), {"a.rom": b"a"})
            make_zip(os.path.join(directory, "b.zip"), {"existing.rom": b"new"})
            with open(os.path.join(directory, "existing.rom"), "wb") as output:
                output.write(b"keep")
            job_id = "test-job"
            proxy.EXTRACT_JOBS[job_id] = {
                "status": "queued", "total": 0, "processed": 0, "completed": 0,
                "failed": 0, "files": 0, "bytes": 0, "current": "", "errors": []
            }
            proxy.ACTIVE_EXTRACT_JOB = job_id

            proxy._run_auto_extract(job_id, directory)

            job = proxy.EXTRACT_JOBS.pop(job_id)
            self.assertEqual(job["status"], "complete")
            self.assertEqual((job["total"], job["processed"]), (2, 2))
            self.assertEqual((job["completed"], job["failed"]), (1, 1))
            self.assertFalse(os.path.exists(os.path.join(directory, "a.zip")))
            self.assertTrue(os.path.isfile(os.path.join(directory, "b.zip")))


if __name__ == "__main__":
    unittest.main()
