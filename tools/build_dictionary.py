"""Build data/dictionary.db from real open data sources.

Sources:
  1. Wiktionary English edition, extracted by wiktextract (kaikki.org JSONL), CC BY-SA 4.0.
  2. FreeDict eng-tur 0.3 TEI source, GPL-2.0-or-later.

Usage:
  python tools/build_dictionary.py --kaikki PATH_TO_JSONL --freedict PATH_TO_eng-tur.tei
  python tools/build_dictionary.py --download   # fetch both sources into build_cache/ first

This is the only part of the project that may use the network.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "dictionary.db"
CACHE = ROOT / "build_cache"
KAIKKI_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
FREEDICT_URL = "https://download.freedict.org/dictionaries/eng-tur/0.3/freedict-eng-tur-0.3.src.tar.xz"

MAX_MEANINGS = 8
HEADWORD_RE = re.compile(r"^[a-z]+(?:['\-][a-z]+)*$")
POS_MAP = {
    "noun": "noun", "verb": "verb", "adj": "adj", "adv": "adv", "prep": "prep",
    "conj": "conj", "pron": "pron", "intj": "interj", "det": "other", "article": "other",
}
SKIP_TAGS = {"obsolete", "archaic", "dated", "rare", "dialectal", "Ottoman-Turkish"}
FORM_TAGS = {"plural", "past", "participle", "comparative", "superlative", "present"}
FORM_SKIP_TAGS = {"alternative", "obsolete", "archaic", "dialectal", "nonstandard", "misspelling", "rare"}
SANITY_WORDS = [
    "the", "be", "have", "house", "water", "run", "book", "good", "quickly", "go",
    "eat", "drink", "big", "small", "red", "dog", "cat", "car", "city", "love",
    "friend", "mother", "father", "child", "school", "work", "happy", "sad", "fast", "slowly",
    "read", "write", "tree", "sun", "and", "with", "because", "beautiful", "time", "day",
]

# word -> pos -> list of (source_priority, tr)
Store = dict[str, dict[str, list[tuple[int, str]]]]


LABEL_RE = re.compile(r"^\([^)]*\)\s*")


def clean_meaning(text: str) -> str | None:
    """Normalize a Turkish meaning; return None if it looks broken."""
    t = " ".join(text.split()).strip().rstrip(".;,").strip()
    if not t or len(t) > 60 or ":" in t or t.startswith("-") or "(bak" in t:
        return None
    if t.count("(") != t.count(")"):
        t = t.replace("(", "").replace(")", "").strip()
    return t or None


def clean_freedict(text: str, headword: str) -> str | None:
    """FreeDict glosses often embed usage labels, English examples and inflections; drop those."""
    t = clean_meaning(LABEL_RE.sub("", text.strip()))
    if t is None or "." in t or "'" in t or "(" in t:
        return None
    if headword in re.findall(r"[a-z']+", t):
        return None
    return t


def add(store: Store, word: str, pos: str, prio: int, tr: str) -> None:
    meaning = clean_meaning(tr) if prio == 0 else clean_freedict(tr, word)
    if meaning is None:
        return
    bucket = store[word][pos]
    if all(m != meaning for _, m in bucket):
        bucket.append((prio, meaning))


def normalize_headword(word: str) -> str | None:
    w = word.strip().lower().replace("\u2019", "'")
    return w if HEADWORD_RE.match(w) else None


def turkish_translations(entry: dict) -> list[dict]:
    items = list(entry.get("translations", []))
    for sense in entry.get("senses", []):
        items.extend(sense.get("translations", []))
    return [t for t in items if t.get("code") == "tr" and t.get("word")
            and not SKIP_TAGS.intersection(t.get("tags", []))]


def collect_forms(entry: dict, lemma: str, forms: dict[str, str]) -> None:
    for f in entry.get("forms", []):
        tags = set(f.get("tags", []))
        if not tags & FORM_TAGS or tags & FORM_SKIP_TAGS:
            continue
        surface = normalize_headword(f.get("form", ""))
        if surface and surface != lemma:
            forms.setdefault(surface, lemma)


def load_kaikki(path: Path, store: Store, forms: dict[str, str]) -> int:
    headwords: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if '"tr"' not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print("  skipped a malformed JSONL line")
                continue
            word = normalize_headword(entry.get("word", ""))
            trs = turkish_translations(entry)
            if not word or not trs:
                continue
            pos = POS_MAP.get(entry.get("pos", ""), "other")
            for t in trs:
                add(store, word, pos, 0, t["word"])
            if word in store:
                headwords.add(word)
                collect_forms(entry, word, forms)
    return len(headwords)


def load_freedict(path: Path, store: Store, forms: dict[str, str]) -> int:
    """Add FreeDict entries for headwords that Wiktionary does not cover."""
    ns = {"t": "http://www.tei-c.org/ns/1.0"}
    covered = set(store)
    skip = covered | set(forms)  # inflected forms (went, children) resolve via the form table
    turkish = {m for poses in store.values() for items in poses.values() for _, m in items}
    headwords: set[str] = set()
    for entry in ET.parse(path).getroot().iterfind(".//t:entry", ns):
        orth = entry.findtext("t:form/t:orth", default="", namespaces=ns)
        word = normalize_headword(orth)
        if not word or word in skip:
            continue
        for quote in entry.iterfind(".//t:cit[@type='trans']/t:quote", ns):
            text = (quote.text or "").strip()
            if text in covered and text not in turkish:  # English cross-reference, not a translation
                continue
            add(store, word, "other", 1, text)
        if store.get(word, {}).get("other"):
            headwords.add(word)
    return len(headwords)


def write_db(store: Store, forms: dict[str, str]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB_PATH.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript("""
        CREATE TABLE entry (id INTEGER PRIMARY KEY, word TEXT NOT NULL, pos TEXT NOT NULL,
                            rank INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE meaning (entry_id INTEGER NOT NULL REFERENCES entry(id), ord INTEGER NOT NULL,
                              tr TEXT NOT NULL, source TEXT NOT NULL);
        CREATE TABLE form (surface TEXT PRIMARY KEY, lemma TEXT NOT NULL);
    """)
    sources = ("wiktionary", "freedict")
    for word in sorted(store):
        for pos, items in store[word].items():
            if not items:
                continue
            items = sorted(items, key=lambda x: x[0])[:MAX_MEANINGS]  # stable: keeps source order
            # rank: Wiktionary-backed parts of speech first, then by number of translations
            rank = (1000 if items[0][0] == 0 else 0) + len(store[word][pos])
            cur = con.execute("INSERT INTO entry (word, pos, rank) VALUES (?, ?, ?)", (word, pos, rank))
            con.executemany("INSERT INTO meaning VALUES (?, ?, ?, ?)",
                            [(cur.lastrowid, i, tr, sources[p]) for i, (p, tr) in enumerate(items)])
    con.executemany("INSERT INTO form VALUES (?, ?)",
                    [(s, l) for s, l in sorted(forms.items()) if l in store])
    con.executescript("""
        CREATE INDEX idx_entry_word ON entry(word);
        CREATE INDEX idx_meaning_entry ON meaning(entry_id, ord);
    """)
    con.commit()
    con.execute("VACUUM")
    con.close()
    tmp.replace(DB_PATH)


def sanity_report(store: Store, forms: dict[str, str]) -> float:
    found = [w for w in SANITY_WORDS if w in store or forms.get(w) in store]
    missing = sorted(set(SANITY_WORDS) - set(found))
    ratio = len(found) / len(SANITY_WORDS)
    print(f"Quality gate: {len(found)}/{len(SANITY_WORDS)} common words found ({ratio:.0%})")
    for w in SANITY_WORDS[:12]:
        first = next(iter(store.get(w, {}).values()), [])
        print(f"  {w:10s} -> {', '.join(m for _, m in first[:3]) or '-'}")
    if missing:
        print("  missing:", ", ".join(missing))
    return ratio


def download(url: str, dest: Path) -> Path:
    if not dest.exists():
        print(f"Downloading {url} ...")
        CACHE.mkdir(exist_ok=True)
        urllib.request.urlretrieve(url, dest)
    return dest


def fetch_sources() -> tuple[Path, Path]:
    kaikki = download(KAIKKI_URL, CACHE / "kaikki-en.jsonl")
    archive = download(FREEDICT_URL, CACHE / "freedict-eng-tur-0.3.src.tar.xz")
    tei = CACHE / "eng-tur" / "eng-tur.tei"
    if not tei.exists():
        with tarfile.open(archive) as tar:
            tar.extract("eng-tur/eng-tur.tei", CACHE)
    return kaikki, tei


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kaikki", type=Path, help="local kaikki.org English JSONL file")
    ap.add_argument("--freedict", type=Path, help="local FreeDict eng-tur.tei file")
    ap.add_argument("--download", action="store_true", help="download missing sources into build_cache/")
    args = ap.parse_args()
    if args.download:
        args.kaikki, args.freedict = fetch_sources()
    if not args.kaikki or not args.kaikki.exists() or not args.freedict or not args.freedict.exists():
        print("ERROR: both source files are required (use --download or pass paths).", file=sys.stderr)
        return 2

    store: Store = defaultdict(lambda: defaultdict(list))
    forms: dict[str, str] = {}
    n_wikt = load_kaikki(args.kaikki, store, forms)
    print(f"Wiktionary: {n_wikt} headwords with Turkish translations")
    n_fd = load_freedict(args.freedict, store, forms)
    print(f"FreeDict:   {n_fd} additional headwords not covered by Wiktionary")
    write_db(store, forms)
    con = sqlite3.connect(DB_PATH)
    for table in ("entry", "meaning", "form"):
        print(f"{table:8s} rows: {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]}")
    print(f"distinct headwords: {con.execute('SELECT COUNT(DISTINCT word) FROM entry').fetchone()[0]}")
    con.close()
    print(f"DB size: {DB_PATH.stat().st_size / 1e6:.1f} MB -> {DB_PATH}")
    if sanity_report(store, forms) < 0.9:
        print("QUALITY GATE FAILED: fewer than 90% of common words have a translation.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
