import importlib.util
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "server.py")
SPEC = importlib.util.spec_from_file_location("artwork_server", MODULE_PATH)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit):
        return self.data[:limit]


class ArtworkTests(unittest.TestCase):
    def test_candidates_clean_common_rom_prefixes_and_region_codes(self):
        candidates = server.artwork_name_candidates("0002 - Super Mario Advance (U) [!].zip")
        self.assertIn("Super Mario Advance (USA)", candidates)
        self.assertIn("Super Mario Advance", candidates)

    def test_title_key_matches_collection_suffix_to_regional_catalog_name(self):
        self.assertEqual(server.artwork_title_key("Banjo-Kazooie # N64.Z64"),
                         server.artwork_title_key("Banjo-Kazooie (USA).png"))

    def test_catalog_prefers_usa_when_multiple_regions_share_title(self):
        listing = (b'<a href="Banjo-Kazooie%20(Europe).png">EU</a>'
                   b'<a href="Banjo-Kazooie%20(USA).png">US</a>')
        catalog = server.artwork_catalog("Nintendo_-_Nintendo_64",
                                         lambda _request, timeout: FakeResponse(listing))
        self.assertEqual(catalog["banjokazooie"], "Banjo-Kazooie (USA)")

    def test_download_validates_png_and_encodes_filename(self):
        png = b"\x89PNG\r\n\x1a\nfixture"
        seen = []

        def opener(request, timeout):
            seen.append((request.full_url, timeout))
            return FakeResponse(png)

        data, matched, url = server._download_artwork("Example", ["Game (USA)"], opener)
        self.assertEqual(data, png)
        self.assertEqual(matched, "Game (USA)")
        self.assertIn("Named_Boxarts/Game%20(USA).png", url)
        self.assertEqual(seen[0][1], 20)

    def test_gamelist_update_is_backed_up_and_preserves_metadata(self):
        original = server.ROMS_ROOT
        with tempfile.TemporaryDirectory() as roms:
            server.ROMS_ROOT = roms
            folder = os.path.join(roms, "snes")
            os.makedirs(folder)
            rom = os.path.join(folder, "Game.zip")
            with open(rom, "wb") as output:
                output.write(b"rom")
            gamelist = os.path.join(folder, "gamelist.xml")
            with open(gamelist, "w", encoding="utf-8") as output:
                output.write("<?xml version='1.0'?><gameList><game><path>./Game.zip</path><name>Custom Name</name><rating>1</rating></game></gameList>")
            try:
                server._write_gamelist("snes", [(rom, "images/game.png", "Ignored")])
                root = ET.parse(gamelist).getroot()
                game = root.find("game")
                self.assertEqual(game.findtext("name"), "Custom Name")
                self.assertEqual(game.findtext("rating"), "1")
                self.assertEqual(game.findtext("image"), "./images/game.png")
                self.assertTrue(os.path.isfile(gamelist + ".lan-batocera.bak"))
            finally:
                server.ROMS_ROOT = original

    def test_library_uses_batocera_name_and_existing_cover_art(self):
        original = server.ROMS_ROOT
        with tempfile.TemporaryDirectory() as roms:
            server.ROMS_ROOT = roms
            folder = os.path.join(roms, "n64")
            os.makedirs(os.path.join(folder, "images"))
            rom = os.path.join(folder, "Legend of Zelda # N64.Z64")
            image = os.path.join(folder, "images", "zelda.png")
            with open(rom, "wb") as output:
                output.write(b"rom")
            with open(image, "wb") as output:
                output.write(b"\x89PNG\r\n\x1a\nfixture")
            with open(os.path.join(folder, "gamelist.xml"), "w", encoding="utf-8") as output:
                output.write("<?xml version='1.0'?><gameList><game>"
                             "<path>./Legend of Zelda # N64.Z64</path>"
                             "<name>The Legend of Zelda: Ocarina of Time</name>"
                             "<image>./images/zelda.png</image>"
                             "</game></gameList>")
            try:
                listing = server.games()
                self.assertEqual(listing[0]["name"], "The Legend of Zelda: Ocarina of Time")
                self.assertEqual(listing[0]["image"], "n64/images/zelda.png")
            finally:
                server.ROMS_ROOT = original

    def test_worker_writes_art_and_marks_job_complete(self):
        original = server.ROMS_ROOT
        with tempfile.TemporaryDirectory() as roms:
            server.ROMS_ROOT = roms
            folder = os.path.join(roms, "snes")
            os.makedirs(folder)
            with open(os.path.join(folder, "Game (USA).zip"), "wb") as output:
                output.write(b"rom")
            job = {"status": "queued", "cancel": False}
            png = b"\x89PNG\r\n\x1a\nfixture"
            try:
                with mock.patch.object(server, "artwork_catalog", return_value={"game": "Game (USA)"}), \
                        mock.patch.object(server, "_download_artwork", return_value=(png, "Game (USA)", "url")), \
                        mock.patch.object(server.time, "sleep"):
                    server._artwork_worker(job, "snes", 10)
                self.assertEqual(job["status"], "complete")
                self.assertEqual(job["downloaded"], 1)
                listing = server.games()
                self.assertIn("image", listing[0])
                self.assertTrue(os.path.isfile(os.path.join(roms, listing[0]["image"])))
            finally:
                server.ROMS_ROOT = original

    def test_library_ui_exposes_artwork_progress_and_images(self):
        filename = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
        with open(filename, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("Fetch Missing Artwork", page)
        self.assertIn("/api/artwork/start", page)
        self.assertIn("artworkBar", page)
        self.assertIn("game-art", page)
        self.assertIn("height:250px", page)
        self.assertIn("gameCopy.className='game-copy'", page)
        self.assertIn("game-link.has-art{display:flex", page)
        self.assertIn(".games{align-items:start}", page)


if __name__ == "__main__":
    unittest.main()
