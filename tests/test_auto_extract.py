import importlib.util
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
