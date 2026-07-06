# ConceptBridge — 中英 Concept Network: Design Spec

**Date:** 2026-07-06
**Owner:** Yunshu Gao
**Status:** Approved design, pending spec review

## 1. Purpose

Yunshu has a rich conceptual world built from Chinese secondary schooling and Chinese-language reading, and needs a dense, permanent mapping from those concepts to the English linguistic system — terminology, collocations, register, and the places where 中英 concepts do *not* map cleanly. The deliverable is a browsable bilingual concept-network website, generated from structured data, deployed to GitHub Pages.

This is a **permanent knowledge base**, not a study aid for one exam. The data layer is the asset; the website is one view of it.

## 2. Corpus and phases

Sources live in `D:\NewGaoYunshu2024\5.Economist\`. The pipeline is format-agnostic: PDF, EPUB, and MOBI are all in scope (library survey: 397 PDF, 68 EPUB, 3 MOBI; MP3 audio and `.lnk` shortcuts out of scope).

| Phase | Scope | Gate |
|---|---|---|
| 0 | Scaffold: repo, schema, validator, build script, one sample chapter end-to-end | User reviews pilot pages |
| 1 | 《世界历史·九年级上册》 complete | User reviews concept quality |
| 2 | Remaining 8 history textbooks (初中历史 ×6 remainder, 高中历史选择性必修 1–3) | — |
| 3 | Remaining 20 textbooks in `History\` (思想政治 ×10, 道德与法治 ×6, 人文地理 ×1, 美术 ×6 — note: actual counts per folder listing) | — |
| 4 | Curated Chinese-language books from the wider `5.Economist` library (all formats). A candidate list is proposed to the user **before** any book is processed. Initial candidates: 道德经 (理雅各双语版), 荀子·劝学, 乡土中国 (From the Soil, 双语), 朱镕基讲话实录, 爱比克泰德论说集, 将人生哲学到底, 居里夫人自传 (双语), 天幕红尘, 基层女性. | User approves book list |
| 5 | GitHub deployment: repo `yunshugao/concept-bridge`, GitHub Pages; redeploy after every subsequent phase | User confirms public vs private repo |

Textbook priority within phases 1–3: history first (user's chosen spine), then politics/civics, geography, art.

## 3. Data layer (single source of truth)

- `data/books.json` — manifest: id, title (zh/en), format, path, phase, status, chapter list.
- `data/concepts/<book-id>.json` — array of concept nodes extracted from that book.
- Cross-book concepts are **merged**: one canonical node id, multiple `sources` entries. The validator flags likely duplicates (same zh term or same en term) for merge.

### Concept node schema

```json
{
  "id": "keju-imperial-examination",
  "zh": "科举制",
  "pinyin": "kējǔ zhì",
  "en": "the imperial examination system",
  "en_alt": ["civil service examinations", "the keju system"],
  "def_zh": "隋唐至清代通过分科考试选拔官员的制度。",
  "def_en": "China's merit-based system (Sui–Qing) of selecting officials through competitive written examinations.",
  "sources": [{"book": "hist-x1", "chapter": "第5课 中国古代官员的选拔与管理"}],
  "collocations": ["sit/pass the imperial examinations", "a meritocratic bureaucracy", "abolish the examination system (1905)"],
  "example": "Long before Northcote and Trevelyan, China had been recruiting its mandarins by competitive examination for a millennium.",
  "nuance": "英语中 meritocracy 是现代概念；描述科举多用 'proto-meritocratic'。",
  "links": [{"to": "jiupin-zhongzheng", "rel": "replaced"}, {"to": "civil-service-uk", "rel": "influenced"}],
  "themes": ["governance", "selection-of-officials"],
  "period": "605–1905"
}
```

Required fields: `id`, `zh`, `en`, `def_zh`, `def_en`, `sources`, `themes`. Optional: `pinyin`, `en_alt`, `collocations`, `example`, `nuance`, `links`, `period`. Every node should aim for all four layers (core mapping, collocations/discourse, cross-links, nuance) where the concept warrants them; `nuance` is mandatory whenever the mapping is contested or misleading (封建, 民主集中制, 民族, 现代化 …).

Link relation vocabulary (extensible): `related`, `broader`, `narrower`, `replaced`, `replaced-by`, `influenced`, `influenced-by`, `contrast`, `cause`, `effect`.

## 4. Build system

`build.py` — single Python script, stdlib only (no pip dependencies). Responsibilities:

1. **Validate**: JSON schema conformance, unique ids, dead-link detection (every `links.to` must resolve), duplicate-term warnings, required-field checks. Build fails on errors.
2. **Generate** static HTML into `site/`:
   - Home — corpus overview, progress by book, entry points by theme/period/book
   - One page per concept (`site/c/<id>.html`) — all layers, clickable related nodes
   - Book and chapter index pages mirroring textbook structure
   - Theme cluster pages
   - Timeline page (nodes with `period`)
   - Graph view — interactive network visualisation, data inlined, no CDN dependencies
   - Search — client-side index (`site/search-index.json`) matching zh, pinyin, en; instant results
3. **No external assets**: all CSS/JS inline or local, so the site works offline and on GitHub Pages.

Design language: clean bilingual side-by-side layout, mobile-friendly, consistent with Yunshu's Game On tutorial aesthetic. Australian English in UI copy.

## 5. Extraction pipeline

Per book:

1. **Read** — PDF: read chapter page-ranges via PDF page reading; EPUB: unzip, parse XHTML chapters (stdlib `zipfile` + HTML parsing); MOBI: convert to EPUB/text first (Calibre `ebook-convert` if available; otherwise defer the book).
2. **Extract** — identify every substantive concept per chapter (institutions, events, doctrines, periods, figures-as-concepts, technical terms). Textbook 正文, 学习聚焦, 历史纵横, and key-term boxes are all fair game.
3. **Author** — write the node: definitions in original wording (never copied textbook passages), Economist-register example sentence, collocations from real English usage, nuance warnings where mapping is unsafe.
4. **Link** — cross-link within the chapter, then across the corpus (the validator's term index helps spot merge/link candidates).
5. **Validate + rebuild** — run `build.py`; fix errors before committing.

Concept granularity guide: a Year-9 world-history chapter yields roughly 10–25 nodes. Prefer fewer, richer nodes over exhaustive keyword lists.

## 6. Guardrails

- **Copyright**: the published site contains only original-wording mappings — terms, self-written definitions, collocations, commentary. No scanned images, no verbatim passages beyond short quoted phrases. Source files (PDFs/EPUBs) are never committed to the repo.
- **Privacy**: only books on the approved corpus list are read. Personal documents in `5.Economist` (employment letters, superannuation statements, application forms, etc.) are permanently out of scope.
- **Versioning**: everything (data, build script, generated site optional) in git with meaningful commits per book/phase.

## 7. Deployment

- GitHub repo `yunshugao/concept-bridge` (visibility decided at Phase 5 gate; default recommendation: public, given the copyright guardrails).
- GitHub Pages serving the `site/` output (via Actions build or committed `site/` — decided at Phase 5; simplest: commit built site, serve from branch).
- Live URL: `https://yunshugao.github.io/concept-bridge/`.

## 8. Success criteria

- Every processed book has its full chapter structure represented, with concept nodes carrying the four layers where warranted.
- Zero dead cross-links; duplicate concepts merged, not repeated.
- Bilingual search finds a node from 中文, pinyin, or English input.
- Site loads offline and on GitHub Pages with no external requests.
- Yunshu can start from any Economist article term and navigate the network back to the Chinese concept and its textbook source.

## 9. Out of scope (YAGNI)

- Anki export, Obsidian export (data layer makes these possible later; not built now).
- Spaced-repetition features, user accounts, comments.
- Audio (MP3s), English-language books as extraction sources (they may inform collocations but are not corpus items in phases 0–4).
- OCR of image-only PDFs beyond what page reading supports — books that resist extraction are deferred, not blocked on.
