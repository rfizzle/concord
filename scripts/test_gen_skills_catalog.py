import importlib.util
import pathlib
import tempfile
import unittest

_spec = importlib.util.spec_from_file_location(
    "gen_skills_catalog", pathlib.Path(__file__).parent / "gen-skills-catalog.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


class LineRefTest(unittest.TestCase):
    def _scan(self, text):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "mc-x").mkdir()
            (root / "mc-x" / "SKILL.md").write_text(text, encoding="utf-8")
            return gen.find_line_refs(root)

    def test_flags_member_line_reference(self):
        self.assertEqual(len(self._scan("meridian's `Foo.java:46-50` here\n")), 1)

    def test_flags_plain_line_reference(self):
        self.assertEqual(len(self._scan("see Bar.gradle:12\n")), 1)

    def test_allows_class_name_only(self):
        self.assertEqual(self._scan("meridian's `ShippedResourceHygieneTest`\n"), [])

    def test_allows_urls_and_ports(self):
        self.assertEqual(self._scan("localhost:25565 and https://x.y/z\n"), [])

    def test_repo_skills_are_clean(self):
        self.assertEqual(gen.find_line_refs(), [])


if __name__ == "__main__":
    unittest.main()
