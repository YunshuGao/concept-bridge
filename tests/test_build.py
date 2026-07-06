import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build import validate

def node(**over):
    base = {
        "id": "keju-imperial-examination",
        "zh": "科举制",
        "en": "the imperial examination system",
        "def_zh": "通过分科考试选拔官员的制度。",
        "def_en": "China's merit-based official-selection system.",
        "sources": [{"book": "wh9a", "chapter": "第1课"}],
        "themes": ["governance"],
    }
    base.update(over)
    return base

class TestValidate(unittest.TestCase):
    def test_valid_data_passes(self):
        errors, warnings = validate([node()], {"wh9a"})
        self.assertEqual(errors, [])

    def test_missing_required_field_is_error(self):
        n = node()
        del n["def_en"]
        errors, _ = validate([n], {"wh9a"})
        self.assertTrue(any("def_en" in e for e in errors))

    def test_duplicate_id_is_error(self):
        errors, _ = validate([node(), node()], {"wh9a"})
        self.assertTrue(any("duplicate id" in e for e in errors))

    def test_dead_link_is_error(self):
        n = node(links=[{"to": "no-such-node", "rel": "related"}])
        errors, _ = validate([n], {"wh9a"})
        self.assertTrue(any("no-such-node" in e for e in errors))

    def test_unknown_book_in_source_is_error(self):
        n = node(sources=[{"book": "nope", "chapter": "x"}])
        errors, _ = validate([n], {"wh9a"})
        self.assertTrue(any("nope" in e for e in errors))

    def test_duplicate_zh_term_is_warning(self):
        a = node()
        b = node(id="keju-2", en="the keju system")
        _, warnings = validate([a, b], {"wh9a"})
        self.assertTrue(any("科举制" in w for w in warnings))

    def test_bad_link_rel_is_error(self):
        a = node()
        b = node(id="other", zh="其他", en="other",
                 links=[{"to": "keju-imperial-examination", "rel": "banana"}])
        errors, _ = validate([a, b], {"wh9a"})
        self.assertTrue(any("banana" in e for e in errors))

import json, tempfile, shutil
from build import generate

class TestGenerate(unittest.TestCase):
    def test_generates_core_pages(self):
        books = [{"id": "wh9a", "title_zh": "世界历史九上", "title_en": "World History 9A",
                  "format": "pdf", "path": "x.pdf", "phase": 1, "status": "in-progress",
                  "chapters": ["第1课 古代埃及"]}]
        a = node(period="前3100年–前30年",
                 links=[{"to": "b-node", "rel": "related"}])
        b = node(id="b-node", zh="乙概念", en="concept B")
        out = Path(tempfile.mkdtemp())
        try:
            generate(books, [a, b], out)
            for p in ["index.html", "c/keju-imperial-examination.html",
                      "book/wh9a.html", "themes.html", "timeline.html",
                      "graph.html", "search-index.json"]:
                self.assertTrue((out / p).exists(), p)
            html = (out / "c/keju-imperial-examination.html").read_text(encoding="utf-8")
            self.assertIn("科举制", html)
            self.assertIn("b-node.html", html)
            idx = json.loads((out / "search-index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(idx), 2)
        finally:
            shutil.rmtree(out)

if __name__ == "__main__":
    unittest.main()
