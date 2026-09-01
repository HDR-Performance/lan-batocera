import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class MobileLibraryTests(unittest.TestCase):
    def test_mobile_search_collapses_and_tiles_are_compact(self):
        page_path = os.path.join(REPOSITORY_ROOT, "web", "index.html")
        with open(page_path, encoding="utf-8") as page_file:
            page = page_file.read()
        self.assertIn('id="mobileSearchToggle"', page)
        self.assertIn('aria-expanded="false"', page)
        self.assertIn("filters:not(.search-open) #search", page)
        self.assertIn("minmax(155px,1fr)", page)
        self.assertIn("height:174px", page)
        self.assertIn("mobileSearchToggle.onclick", page)


if __name__ == "__main__":
    unittest.main()
