"""ConceptBridge build: validate the concept data and generate the static site."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"

REQUIRED = ["id", "zh", "en", "def_zh", "def_en", "sources", "themes"]
OPTIONAL = ["pinyin", "en_alt", "collocations", "example", "nuance", "links", "period",
            "pron", "etymology", "synonyms"]
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


from html import escape
from templates import page, graph_page

REL_ZH = {"related": "相关", "broader": "上位", "narrower": "下位",
          "replaced": "取代了", "replaced-by": "被取代于", "influenced": "影响了",
          "influenced-by": "受影响于", "contrast": "对比", "cause": "原因",
          "effect": "结果"}


def node_link(n, root=""):
    return (f'<a class="node" href="{root}c/{n["id"]}.html">'
            f'{escape(n["zh"])} · {escape(n["en"])}</a>')


def concept_page(n, by_id, backlinks):
    b = [f'<h1>{escape(n["zh"])} '
         f'<span class="pinyin">{escape(n.get("pinyin", ""))}</span>'
         f'<span class="en">{escape(n["en"])}</span></h1>']
    if n.get("pron"):
        b.append(f'<p class="meta">🔊 <span class="ipa">{escape(n["pron"])}</span></p>')
    if n.get("en_alt"):
        b.append('<p class="meta">also: ' + " · ".join(escape(x) for x in n["en_alt"]) + "</p>")
    if n.get("period"):
        b.append(f'<p class="meta">⏳ {escape(n["period"])}</p>')
    b.append(f'<div class="card"><p class="zh">{escape(n["def_zh"])}</p>'
             f'<p class="endef">{escape(n["def_en"])}</p></div>')
    if n.get("etymology"):
        b.append(f"<h2>Etymology 词源</h2><div class='card'><p>{escape(n['etymology'])}</p></div>")
    if n.get("synonyms"):
        rows = "".join(
            f"<li>▸ <b>{escape(s['word'])}</b> "
            f"<span class='ipa'>{escape(s.get('ipa',''))}</span><br>"
            f"<em>{escape(s.get('sentence',''))}</em></li>"
            for s in n["synonyms"])
        b.append(f"<h2>Synonyms 近义词</h2><div class='card'><ul class='plain'>{rows}</ul></div>")
    if n.get("collocations"):
        b.append("<h2>Collocations 常用搭配</h2><div class='card'><ul class='plain'>"
                 + "".join(f"<li>▸ {escape(c)}</li>" for c in n["collocations"])
                 + "</ul></div>")
    if n.get("example"):
        b.append(f"<h2>In the wild 语境例句</h2><div class='card'>"
                 f"<p><em>{escape(n['example'])}</em></p></div>")
    if n.get("nuance"):
        b.append(f"<h2>Nuance 陷阱与辨析</h2><div class='card nuance'>"
                 f"<p>{escape(n['nuance'])}</p></div>")
    rels = [f'<li><span class="rel">{REL_ZH.get(l["rel"], l["rel"])} {escape(l["rel"])}</span> '
            + node_link(by_id[l["to"]], "../") + "</li>"
            for l in n.get("links", []) if l["to"] in by_id]
    rels += ['<li><span class="rel">← linked from</span> ' + node_link(by_id[src], "../") + "</li>"
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
        body = [f'<h1>{escape(bk["title_zh"])}'
                f'<span class="en">{escape(bk["title_en"])}</span></h1>']
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
        tb.append(f'<h2 id="{escape(t)}">#{escape(t)} '
                  f'<span class="count">({len(themes[t])})</span></h2>'
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
    lb += [f"<li class='card'><span class='meta'>{escape(n['period'])}</span><br>"
           f"{node_link(n)}</li>" for n in dated]
    lb.append("</ul>")
    (out / "timeline.html").write_text(page("Timeline", "\n".join(lb)), encoding="utf-8")

    # search index: t = lowercase searchable tokens
    idx = [{"id": n["id"], "zh": n["zh"], "en": n["en"],
            "t": [x.lower() for x in
                  [n["zh"], n.get("pinyin", ""), n["en"], *n.get("en_alt", [])] if x]}
           for n in nodes]
    (out / "search-index.json").write_text(
        json.dumps(idx, ensure_ascii=False), encoding="utf-8")

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


if __name__ == "__main__":
    main()
