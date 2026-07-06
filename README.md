# ConceptBridge 中英概念桥

A bilingual concept network mapping concepts from Chinese secondary textbooks
(and Chinese-language books) to their English discourse layer — terminology,
collocations, register and false-friend warnings.

- `data/` — the knowledge base (single source of truth)
- `build.py` — validates the data and generates the static site into `site/`
- Spec: `docs/superpowers/specs/2026-07-06-conceptbridge-design.md`

Build: `python build.py`
Test:  `python -m unittest discover tests -v`
