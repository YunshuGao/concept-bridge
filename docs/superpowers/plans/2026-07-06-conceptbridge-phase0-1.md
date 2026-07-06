# ConceptBridge Phase 0–1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ConceptBridge data schema, validator and static-site generator, then populate it with the complete concept network for 《世界历史·九年级上册》.

**Architecture:** JSON concept store (`data/`) → `build.py` validates and generates a static multi-page bilingual site into `site/`. HTML/CSS/JS live as constants in `templates.py`. Content is authored by reading textbook PDF chapters and writing concept nodes that pass validation.

**Tech Stack:** Python 3 stdlib only (json, pathlib, unittest). No pip installs. Generated site: vanilla HTML/CSS/JS, zero external requests.

**Working directory for all commands:** `D:\NewGaoYunshu2024\5.Economist\ConceptBridge`

---

## File structure

```
ConceptBridge/
├── build.py                 # load → validate → generate; CLI entry point
├── templates.py             # HTML page templates, CSS, search JS, graph JS (constants + small fns)
├── tests/
│   └── test_build.py        # unittest suite for validator + generator smoke tests
├── data/
│   ├── books.json           # corpus manifest
│   └── concepts/
│       └── wh9a.json        # 世界历史·九年级上册 concept nodes
├── site/                    # generated output (committed, served by GitHub Pages later)
└── docs/superpowers/...     # spec + this plan
```

Book id convention: `wh9a` = 世界历史九年级上册, `wh9b` = 九下, `ch7a`/`ch7b`/`ch8a`/`ch8b` = 中国历史七/八年级上/下, `hx1`–`hx3` = 高中历史选择性必修1–3. (Later phases extend this.)

---

### Task 1: Repo scaffold and manifest

**Files:**
- Create: `.gitignore`, `README.md`, `data/books.json`, `data/concepts/wh9a.json`

- [ ] **Step 1: Verify Python is available**

Run: `python --version`
Expected: `Python 3.x`. If missing, try `py --version` and use `py` for all later commands.

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
```

- [ ] **Step 3: Write `README.md`**

```markdown
# ConceptBridge 中英概念桥

A bilingual concept network mapping concepts from Chinese secondary textbooks
(and Chinese-language books) to their English discourse layer — terminology,
collocations, register and false-friend warnings.

- `data/` — the knowledge base (single source of truth)
- `build.py` — validates the data and generates the static site into `site/`
- Spec: `docs/superpowers/specs/2026-07-06-conceptbridge-design.md`

Build: `python build.py`
Test:  `python -m unittest discover tests -v`
```

- [ ] **Step 4: Write `data/books.json`**

```json
{
  "books": [
    {
      "id": "wh9a",
      "title_zh": "义务教育教科书·世界历史 九年级上册",
      "title_en": "World History, Year 9 Volume 1",
      "format": "pdf",
      "path": "../History/义务教育教科书·世界历史九年级上册.pdf",
      "phase": 1,
      "status": "in-progress",
      "chapters": []
    }
  ]
}
```

`chapters` is filled in Task 7 once the PDF's table of contents has been read.

- [ ] **Step 5: Write empty `data/concepts/wh9a.json`**

```json
[]
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: scaffold data layer and manifest"
```

---

### Task 2: Validator (TDD)

**Files:**
- Create: `tests/test_build.py`, `build.py`

- [ ] **Step 1: Write failing tests for the validator**

`tests/test_build.py`:

```python
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

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_build -v`
Expected: FAIL / ERROR (`build` module or `validate` not found).

- [ ] **Step 3: Implement the validator in `build.py`**

```python
"""ConceptBridge build: validate the concept data and generate the static site."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"

REQUIRED = ["id", "zh", "en", "def_zh", "def_en", "sources", "themes"]
OPTIONAL = ["pinyin", "en_alt", "collocations", "example", "nuance", "links", "period"]
LINK_RELS = {"related", "broader", "narrower", "replaced", "replaced-by",
             "influenced", "influenced-by", "contrast", "cause", "effect"}


def load_books():
    manifest = json.loads((DATA / "books.json").read_text(encoding="utf-8"))
    return manifest["books"]


def load_concepts(books):
    nodes = []
    for book in books:
        f = DATA / "concepts" / f"{book['id']}.json"
        if f.exists():
            nodes.extend(json.loads(f.read_text(encoding="utf-8")))
    return nodes


def validate(nodes, book_ids):
    errors, warnings = [], []
    ids = {}
    zh_seen, en_seen = {}, {}
    for n in nodes:
        nid = n.get("id", "<missing id>")
        for field in REQUIRED:
            if not n.get(field):
                errors.append(f"{nid}: missing required field '{field}'")
        unknown = set(n) - set(REQUIRED) - set(OPTIONAL)
        if unknown:
            errors.append(f"{nid}: unknown fields {sorted(unknown)}")
        if nid in ids:
            errors.append(f"{nid}: duplicate id")
        ids[nid] = n
        for s in n.get("sources", []):
            if s.get("book") not in book_ids:
                errors.append(f"{nid}: source book '{s.get('book')}' not in manifest")
        zh = n.get("zh")
        if zh in zh_seen:
            warnings.append(f"duplicate zh term '{zh}' in {zh_seen[zh]} and {nid} — merge?")
        else:
            zh_seen[zh] = nid
        en = (n.get("en") or "").lower()
        if en in en_seen:
            warnings.append(f"duplicate en term '{n.get('en')}' in {en_seen[en]} and {nid} — merge?")
        else:
            en_seen[en] = nid
    for n in nodes:
        for link in n.get("links", []):
            if link.get("to") not in ids:
                errors.append(f"{n['id']}: dead link to '{link.get('to')}'")
            if link.get("rel") not in LINK_RELS:
                errors.append(f"{n['id']}: bad link rel '{link.get('rel')}'")
    return errors, warnings


def main():
    books = load_books()
    nodes = load_concepts(books)
    errors, warnings = validate(nodes, {b["id"] for b in books})
    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        for e in errors:
            print(f"ERROR {e}")
        sys.exit(1)
    print(f"OK    {len(nodes)} concepts across {len(books)} book(s)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_build -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: concept data validator with tests"
```

---

### Task 3: Templates module

**Files:**
- Create: `templates.py`

The whole site shares one shell: header with bilingual search box, content area, footer. All CSS inline in `<style>`, all JS inline in `<script>`. Relative links only (site must work from a subpath on GitHub Pages and from `file://`).

- [ ] **Step 1: Write `templates.py`**

```python
"""HTML templates for the ConceptBridge static site. Stdlib only."""
from html import escape

CSS = """
:root { --ink:#1a1a2e; --acc:#b4373a; --acc2:#1f6f8b; --bg:#faf8f4; --card:#ffffff;
        --muted:#6b6b7b; --line:#e5e0d8; }
* { box-sizing:border-box; margin:0; }
body { font-family:'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
       background:var(--bg); color:var(--ink); line-height:1.65; }
header { background:var(--ink); color:#fff; padding:.8rem 1.2rem;
         display:flex; gap:1rem; align-items:center; flex-wrap:wrap; }
header a { color:#fff; text-decoration:none; font-weight:600; }
header .crumb { color:#bbb; font-weight:400; font-size:.9rem; }
#q { flex:1; min-width:180px; max-width:420px; padding:.45rem .7rem;
     border-radius:6px; border:none; font-size:1rem; }
#results { position:absolute; top:3.4rem; right:1.2rem; left:auto; width:min(480px,90vw);
           background:var(--card); border:1px solid var(--line); border-radius:8px;
           box-shadow:0 8px 24px rgba(0,0,0,.18); max-height:60vh; overflow:auto; z-index:9; }
#results a { display:block; padding:.55rem .8rem; color:var(--ink);
             text-decoration:none; border-bottom:1px solid var(--line); }
#results a:hover { background:var(--bg); }
main { max-width:920px; margin:0 auto; padding:1.4rem 1.2rem 4rem; }
h1 { font-size:1.7rem; margin:.8rem 0 .3rem; }
h1 .en { color:var(--acc2); display:block; font-size:1.15rem; font-weight:600; }
h2 { font-size:1.05rem; color:var(--acc); margin:1.5rem 0 .5rem;
     text-transform:uppercase; letter-spacing:.06em; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:1rem 1.2rem; margin:.6rem 0; }
.zh { font-size:1.02rem; } .endef { color:var(--acc2); margin-top:.3rem; }
.pinyin { color:var(--muted); font-style:italic; }
.tag { display:inline-block; background:#eee7db; border-radius:99px; padding:.1rem .7rem;
       font-size:.82rem; margin:.15rem .25rem .15rem 0; color:var(--ink);
       text-decoration:none; }
.nuance { border-left:4px solid var(--acc); background:#fdf1f1; }
ul.plain { list-style:none; padding:0; } ul.plain li { padding:.2rem 0; }
.rel { color:var(--muted); font-size:.85rem; margin-right:.4rem; }
a.node { color:var(--acc2); text-decoration:none; font-weight:600; }
a.node:hover { text-decoration:underline; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:.6rem; }
.meta { color:var(--muted); font-size:.88rem; }
footer { text-align:center; color:var(--muted); font-size:.85rem; padding:2rem 0; }
canvas { width:100%; background:var(--card); border:1px solid var(--line); border-radius:10px; }
.count { color:var(--muted); font-weight:400; font-size:1rem; }
"""

SEARCH_JS = """
const box=document.getElementById('q'),res=document.getElementById('results');
let IDX=null;
async function idx(){ if(!IDX){ const r=await fetch(ROOT+'search-index.json');
  IDX=await r.json(); } return IDX; }
box&&box.addEventListener('input',async()=>{
  const q=box.value.trim().toLowerCase();
  if(!q){res.style.display='none';return;}
  const d=await idx();
  const hits=d.filter(e=>e.t.some(t=>t.includes(q))).slice(0,20);
  res.innerHTML=hits.map(e=>`<a href="${ROOT}c/${e.id}.html"><b>${e.zh}</b> · ${e.en}</a>`).join('')
    ||'<a>无结果 · no results</a>';
  res.style.display='block';
});
document.addEventListener('click',e=>{ if(res&&!res.contains(e.target)&&e.target!==box)
  res.style.display='none'; });
"""


def page(title, body, root="", crumb=""):
    """root: relative prefix back to site root, e.g. '' or '../'."""
    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · ConceptBridge</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <a href="{root}index.html">概念桥 ConceptBridge</a>
  <span class="crumb">{crumb}</span>
  <input id="q" type="search" placeholder="搜索 search: 科举 / keju / examination…"
         autocomplete="off">
  <div id="results" style="display:none"></div>
</header>
<main>
{body}
</main>
<footer>ConceptBridge · 中英概念网络 · generated by build.py</footer>
<script>const ROOT="{root}";{SEARCH_JS}</script>
</body>
</html>"""
```

- [ ] **Step 2: Smoke-check it imports**

Run: `python -c "import templates; print(len(templates.page('t','b')))"`
Expected: a number > 1000, no traceback.

- [ ] **Step 3: Commit**

```bash
git add templates.py && git commit -m "feat: site shell template with bilingual search UI"
```

---

### Task 4: Site generator — concept, book, theme, timeline and home pages

**Files:**
- Modify: `build.py` (add generation functions + call from `main`)
- Modify: `tests/test_build.py` (add smoke test)

- [ ] **Step 1: Add failing smoke test**

Append to `tests/test_build.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `python -m unittest tests.test_build -v`
Expected: `test_generates_core_pages` ERRORs (no `generate`); validator tests still pass.

- [ ] **Step 3: Implement generation in `build.py`**

Add after the validator (uses `templates.page`, `html.escape`):

```python
from html import escape
from templates import page

REL_ZH = {"related": "相关", "broader": "上位", "narrower": "下位",
          "replaced": "取代了", "replaced-by": "被取代于", "influenced": "影响了",
          "influenced-by": "受影响于", "contrast": "对比", "cause": "原因",
          "effect": "结果"}


def node_link(n, root=""):
    return f'<a class="node" href="{root}c/{n["id"]}.html">{escape(n["zh"])} · {escape(n["en"])}</a>'


def concept_page(n, by_id, backlinks):
    b = [f'<h1>{escape(n["zh"])} '
         f'<span class="pinyin">{escape(n.get("pinyin", ""))}</span>'
         f'<span class="en">{escape(n["en"])}</span></h1>']
    if n.get("en_alt"):
        b.append('<p class="meta">also: ' + " · ".join(escape(x) for x in n["en_alt"]) + "</p>")
    if n.get("period"):
        b.append(f'<p class="meta">⏳ {escape(n["period"])}</p>')
    b.append(f'<div class="card"><p class="zh">{escape(n["def_zh"])}</p>'
             f'<p class="endef">{escape(n["def_en"])}</p></div>')
    if n.get("collocations"):
        b.append("<h2>Collocations 常用搭配</h2><div class='card'><ul class='plain'>"
                 + "".join(f"<li>▸ {escape(c)}</li>" for c in n["collocations"])
                 + "</ul></div>")
    if n.get("example"):
        b.append(f"<h2>In the wild 语境例句</h2><div class='card'><p><em>{escape(n['example'])}</em></p></div>")
    if n.get("nuance"):
        b.append(f"<h2>Nuance 陷阱与辨析</h2><div class='card nuance'><p>{escape(n['nuance'])}</p></div>")
    rels = [f'<li><span class="rel">{REL_ZH.get(l["rel"], l["rel"])} {escape(l["rel"])}</span> '
            + node_link(by_id[l["to"]], "../")
            for l in n.get("links", []) if l["to"] in by_id]
    rels += [f'<li><span class="rel">← linked from</span> ' + node_link(by_id[src], "../")
             for src in backlinks.get(n["id"], [])]
    if rels:
        b.append("<h2>Network 概念网络</h2><div class='card'><ul class='plain'>"
                 + "".join(rels) + "</ul></div>")
    b.append("<h2>Source 出处</h2><p class='meta'>"
             + " · ".join(f"{escape(s['book'])} {escape(s['chapter'])}" for s in n["sources"])
             + "</p>")
    b.append("<p>" + "".join(f'<a class="tag" href="../themes.html#{escape(t)}">#{escape(t)}</a>'
                             for t in n["themes"]) + "</p>")
    crumb = escape(n["sources"][0]["chapter"]) if n["sources"] else ""
    return page(f'{n["zh"]} · {n["en"]}', "\n".join(b), root="../", crumb=crumb)


def generate(books, nodes, out):
    out = Path(out)
    (out / "c").mkdir(parents=True, exist_ok=True)
    (out / "book").mkdir(exist_ok=True)
    by_id = {n["id"]: n for n in nodes}
    backlinks = {}
    for n in nodes:
        for l in n.get("links", []):
            backlinks.setdefault(l["to"], []).append(n["id"])

    for n in nodes:
        (out / "c" / f'{n["id"]}.html').write_text(
            concept_page(n, by_id, backlinks), encoding="utf-8")

    # book pages, grouped by chapter in manifest order
    for bk in books:
        chapters = {c: [] for c in bk.get("chapters", [])}
        for n in nodes:
            for s in n["sources"]:
                if s["book"] == bk["id"]:
                    chapters.setdefault(s["chapter"], []).append(n)
        body = [f'<h1>{escape(bk["title_zh"])}<span class="en">{escape(bk["title_en"])}</span></h1>']
        for ch, ns in chapters.items():
            body.append(f"<h2>{escape(ch)} <span class='count'>({len(ns)})</span></h2>"
                        "<div class='grid'>"
                        + "".join(f"<div class='card'>{node_link(n, '../')}</div>" for n in ns)
                        + "</div>")
        (out / "book" / f'{bk["id"]}.html').write_text(
            page(bk["title_zh"], "\n".join(body), root="../"), encoding="utf-8")

    # themes page
    themes = {}
    for n in nodes:
        for t in n["themes"]:
            themes.setdefault(t, []).append(n)
    tb = ["<h1>Themes 主题群</h1>"]
    for t in sorted(themes):
        tb.append(f'<h2 id="{escape(t)}">#{escape(t)} <span class="count">({len(themes[t])})</span></h2>'
                  "<div class='grid'>"
                  + "".join(f"<div class='card'>{node_link(n)}</div>" for n in themes[t])
                  + "</div>")
    (out / "themes.html").write_text(page("Themes", "\n".join(tb)), encoding="utf-8")

    # timeline page (sort by first number in period; BCE via 前/BC marker)
    import re as _re
    def sort_key(n):
        m = _re.search(r"(前|BC[E]?\s*)?(\d+)", n.get("period", ""))
        if not m:
            return 10 ** 9
        year = int(m.group(2))
        return -year if m.group(1) else year
    dated = sorted([n for n in nodes if n.get("period")], key=sort_key)
    lb = ["<h1>Timeline 时间轴</h1><ul class='plain'>"]
    lb += [f"<li class='card'><span class='meta'>{escape(n['period'])}</span><br>{node_link(n)}</li>"
           for n in dated]
    lb.append("</ul>")
    (out / "timeline.html").write_text(page("Timeline", "\n".join(lb)), encoding="utf-8")

    # search index: t = lowercase searchable tokens
    idx = [{"id": n["id"], "zh": n["zh"], "en": n["en"],
            "t": [x.lower() for x in
                  [n["zh"], n.get("pinyin", ""), n["en"], *n.get("en_alt", [])] if x]}
           for n in nodes]
    (out / "search-index.json").write_text(
        json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    # graph page (Task 6 fills in real force layout; placeholder call here)
    from templates import graph_page
    (out / "graph.html").write_text(graph_page(nodes), encoding="utf-8")

    # home
    hb = [f"<h1>概念桥 <span class='en'>ConceptBridge — {len(nodes)} concepts</span></h1>",
          "<p>已掌握的中文概念世界 × 英语话语体系。A dense bilingual network built from "
          "Chinese secondary textbooks and books.</p>",
          "<h2>Explore 入口</h2><div class='grid'>",
          "<div class='card'><a class='node' href='themes.html'>主题群 Themes</a></div>",
          "<div class='card'><a class='node' href='timeline.html'>时间轴 Timeline</a></div>",
          "<div class='card'><a class='node' href='graph.html'>网络图 Graph</a></div>",
          "</div><h2>Books 书目</h2>"]
    for bk in books:
        cnt = sum(1 for n in nodes if any(s["book"] == bk["id"] for s in n["sources"]))
        hb.append(f"<div class='card'><a class='node' href='book/{bk['id']}.html'>"
                  f"{escape(bk['title_zh'])}</a> <span class='meta'>{escape(bk['title_en'])}"
                  f" · {cnt} concepts · {escape(bk['status'])}</span></div>")
    (out / "index.html").write_text(page("Home", "\n".join(hb)), encoding="utf-8")
```

And extend `main()` so a successful validation generates the site:

```python
def main():
    books = load_books()
    nodes = load_concepts(books)
    errors, warnings = validate(nodes, {b["id"] for b in books})
    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        for e in errors:
            print(f"ERROR {e}")
        sys.exit(1)
    generate(books, nodes, SITE)
    print(f"OK    {len(nodes)} concepts across {len(books)} book(s) -> {SITE}")
```

Add a minimal `graph_page` stub to `templates.py` so Task 4 is self-contained (replaced in Task 6):

```python
def graph_page(nodes):
    return page("Graph", "<h1>网络图 Graph</h1><p>Coming in Task 6.</p>")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_build -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: static site generator (concept/book/theme/timeline/home/search)"
```

---

### Task 5: Interactive graph view

**Files:**
- Modify: `templates.py` (replace `graph_page` stub)

- [ ] **Step 1: Replace `graph_page` with a real force-directed canvas**

```python
GRAPH_JS = """
const cv=document.getElementById('g'),ctx=cv.getContext('2d');
const W=cv.width=cv.clientWidth*devicePixelRatio,H=cv.height=560*devicePixelRatio;
const N=GDATA.nodes.map((n,i)=>({...n,x:Math.random()*W,y:Math.random()*H,vx:0,vy:0}));
const byId=Object.fromEntries(N.map(n=>[n.id,n]));
const E=GDATA.edges.filter(e=>byId[e.s]&&byId[e.t]);
function step(){
  for(const a of N){a.vx*=.6;a.vy*=.6;
    for(const b of N){ if(a===b)continue;
      let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+40;const f=1800*devicePixelRatio/d2;
      a.vx+=dx*f/Math.sqrt(d2);a.vy+=dy*f/Math.sqrt(d2);}
    a.vx+=(W/2-a.x)*.0012;a.vy+=(H/2-a.y)*.0012;}
  for(const e of E){const s=byId[e.s],t=byId[e.t];
    const dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-90*devicePixelRatio)*.004;
    s.vx+=dx/d*f;s.vy+=dy/d*f;t.vx-=dx/d*f;t.vy-=dy/d*f;}
  for(const n of N){n.x+=n.vx;n.y+=n.vy;
    n.x=Math.max(20,Math.min(W-20,n.x));n.y=Math.max(20,Math.min(H-20,n.y));}
}
function draw(){
  ctx.clearRect(0,0,W,H);ctx.strokeStyle='#d8d2c6';
  for(const e of E){const s=byId[e.s],t=byId[e.t];
    ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);ctx.stroke();}
  ctx.font=`${11*devicePixelRatio}px sans-serif`;ctx.textAlign='center';
  for(const n of N){ctx.fillStyle='#1f6f8b';
    ctx.beginPath();ctx.arc(n.x,n.y,5*devicePixelRatio,0,7);ctx.fill();
    ctx.fillStyle='#1a1a2e';ctx.fillText(n.zh,n.x,n.y-9*devicePixelRatio);}
}
let ticks=0;(function loop(){step();draw();if(++ticks<400)requestAnimationFrame(loop);})();
cv.addEventListener('click',ev=>{
  const r=cv.getBoundingClientRect();
  const x=(ev.clientX-r.left)*devicePixelRatio,y=(ev.clientY-r.top)*devicePixelRatio;
  for(const n of N){ if((n.x-x)**2+(n.y-y)**2<180)location.href='c/'+n.id+'.html';}
});
"""


def graph_page(nodes):
    import json as _json
    data = {
        "nodes": [{"id": n["id"], "zh": n["zh"]} for n in nodes],
        "edges": [{"s": n["id"], "t": l["to"]}
                  for n in nodes for l in n.get("links", [])],
    }
    body = ("<h1>网络图 <span class='en'>Concept graph — click a node</span></h1>"
            "<canvas id='g' style='height:560px'></canvas>"
            f"<script>const GDATA={_json.dumps(data, ensure_ascii=False)};{GRAPH_JS}</script>")
    return page("Graph", body)
```

- [ ] **Step 2: Run tests (still green) and rebuild**

Run: `python -m unittest tests.test_build -v && python build.py`
Expected: tests PASS; `OK 0 concepts…` (data still empty) and `site/` regenerated.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: force-directed concept graph view"
```

---

### Task 6: Pilot chapter — 第1课 from 《世界历史·九年级上册》

**Files:**
- Modify: `data/books.json` (fill `chapters`), `data/concepts/wh9a.json`

- [ ] **Step 1: Read the book's table of contents**

Read pages 1–10 of `D:\NewGaoYunshu2024\5.Economist\History\义务教育教科书·世界历史九年级上册.pdf` (Read tool, `pages` parameter). Record the full 单元/课 structure into `books.json` → `chapters` (one entry per 课, format `第N课 标题`).

- [ ] **Step 2: Read 第1课 in full**

Locate its page range from the TOC and read those pages.

- [ ] **Step 3: Author concept nodes for 第1课**

Write 10–25 nodes into `data/concepts/wh9a.json` following the spec schema. Authoring rules (apply to every content task in this plan):

- `def_zh`/`def_en` in original wording — never OCR text.
- `def_en` in the register of serious English prose (Economist/academic), not translationese.
- `collocations`: real English verb/noun patterns for the term.
- `example`: one Economist-register sentence using the term naturally.
- `nuance`: mandatory where the mapping misleads (e.g. 法老 pharaoh is safe; 种姓制度 caste needs the varna/jati distinction; 封建 vs feudalism flagged whenever it appears).
- `links`: connect within the chapter now; cross-chapter/cross-book links added as the corpus grows.
- `themes` from a small controlled set (governance, economy, religion, war, culture, science-tech, society, geography-environment, ideas).
- ids: lowercase-kebab, English-led, stable (e.g. `hammurabi-code`, `nile-civilization`).

Example node (第1课 古代埃及):

```json
{
  "id": "pharaoh",
  "zh": "法老",
  "pinyin": "fǎlǎo",
  "en": "pharaoh",
  "def_zh": "古埃及的最高统治者，被视为神在人间的化身，集政治与宗教权力于一身。",
  "def_en": "The god-king of ancient Egypt, holding absolute political and religious authority as the living embodiment of divine order.",
  "sources": [{"book": "wh9a", "chapter": "第1课 古代埃及"}],
  "collocations": ["under the pharaohs", "pharaonic rule/power", "the pharaoh's divine authority"],
  "example": "Egypt's bureaucratic tradition long predates the modern state: the pharaohs were levying grain taxes four millennia before the IRS.",
  "nuance": "英语中 pharaonic 可作比喻，形容工程浩大或权力集中（a pharaonic infrastructure project），中文无此引申用法。",
  "links": [{"to": "nile-civilization", "rel": "related"}, {"to": "pyramids", "rel": "related"}],
  "themes": ["governance", "religion"],
  "period": "前3100年–前30年"
}
```

- [ ] **Step 4: Validate and build**

Run: `python build.py`
Expected: `OK <n> concepts…`, site regenerated. Fix any ERROR lines before continuing.

- [ ] **Step 5: Visual check**

Open `site/index.html` and the new concept pages; verify search finds nodes by 中文, pinyin and English; graph renders and is clickable.

- [ ] **Step 6: Commit — PHASE 0 GATE**

```bash
git add -A && git commit -m "content(wh9a): pilot chapter 第1课 concepts"
```

Present pilot pages to Yunshu for review. **In an autonomous run, continue to Task 7 and flag the gate in the final report.**

---

### Task 7: Complete 《世界历史·九年级上册》 (Phase 1)

**Files:**
- Modify: `data/concepts/wh9a.json`, `data/books.json` (status → `complete`)

The book has ~7 单元 / ~21 课. Process **one 单元 at a time**, repeating the Task 6 loop:

- [ ] **Step 1: For each 单元 (2–4 课):** read pages → author nodes per 课 (10–25 each, same rules) → add intra-unit links → `python build.py` → fix errors → commit `content(wh9a): 第N单元 concepts`.
- [ ] **Step 2: Cross-linking pass** — after all units: scan the full node list; add cross-unit links (e.g. 罗马共和国 ↔ 雅典民主 `contrast`; 文艺复兴 ↔ 古典文化 `influenced-by`). Aim: no orphan nodes (validator warnings guide this).
- [ ] **Step 3: Dedup pass** — resolve every duplicate-term warning by merging nodes (union of sources/links/collocations).
- [ ] **Step 4: Final build + tests**

Run: `python -m unittest tests.test_build -v && python build.py`
Expected: tests PASS, zero ERROR, warnings resolved or consciously accepted.

- [ ] **Step 5: Mark book complete and commit — PHASE 1 GATE**

Set `"status": "complete"` in `books.json`.

```bash
git add -A && git commit -m "content(wh9a): complete 世界历史九上 concept network"
```

Report to Yunshu: node count, theme distribution, sample pages to review.

---

## Self-review notes

- Spec coverage: schema ✔ (Task 2 validator enforces it), build ✔ (Tasks 3–5), all site pages from spec §4 ✔ (home/concept/book/themes/timeline/graph/search), extraction pipeline ✔ (Tasks 6–7 encode spec §5 rules), guardrails ✔ (authoring rules forbid verbatim text; PDFs never committed — not in repo dir). Phases 2–5 are out of this plan by design (separate plans per phase).
- Types consistent: `validate(nodes, book_ids) -> (errors, warnings)`; `generate(books, nodes, out)`; `page(title, body, root, crumb)`; `graph_page(nodes)` — used identically across tasks.
- MOBI/EPUB readers not needed until Phase 4; YAGNI — excluded here.
