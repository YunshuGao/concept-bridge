"""Merge a unit fragment JSON into a book's concept file. Usage:
python data/merge_fragment.py <book-id> <fragment-path>
"""
import json
import sys
from pathlib import Path

book, frag = sys.argv[1], sys.argv[2]
target = Path(__file__).parent / "concepts" / f"{book}.json"
existing = json.loads(target.read_text(encoding="utf-8"))
new = json.loads(Path(frag).read_text(encoding="utf-8"))
ids = {n["id"] for n in existing}
added = [n for n in new if n["id"] not in ids]
existing.extend(added)
target.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"added {len(added)} nodes -> {target.name} (total {len(existing)})")
