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
