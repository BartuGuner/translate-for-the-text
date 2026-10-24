"""Tokenizer and word lookup."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterator

import simplemma

from .dictionary import Dictionary, Sense

WORD_RE = re.compile(r"[A-Za-z]+(?:['\u2019\-][A-Za-z]+)*")
SENTENCE_END = ".!?\n\"'\u201c\u2018(["
SINGLE_LETTER_WORDS = {"a", "i"}
NEGATIVE_BASE = {"can't": "can", "won't": "will", "shan't": "shall", "ain't": "be",
                 "isn't": "be", "aren't": "be", "wasn't": "be", "weren't": "be"}
CONTRACTION_SUFFIXES = ("'re", "'ve", "'ll", "'m", "'d")

Segment = dict


def tokenize(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_word, segment) pairs. Joining all segments returns the input."""
    out: list[tuple[bool, str]] = []
    pos = 0
    for m in WORD_RE.finditer(text):
        if m.start() > pos:
            out.append((False, text[pos:m.start()]))
        out.append((True, m.group()))
        pos = m.end()
    if pos < len(text):
        out.append((False, text[pos:]))
    return out


def split_contraction(t: str) -> tuple[str, bool] | None:
    """Return (base word, is_negative) for contractions like don't, I'm, we'll."""
    if t in NEGATIVE_BASE:
        return NEGATIVE_BASE[t], True
    if t.endswith("n't"):
        return t[:-3], True
    for suffix in CONTRACTION_SUFFIXES:
        if t.endswith(suffix):
            return t[: -len(suffix)], False
    return None


def candidates(t: str, forms: dict[str, str]) -> Iterator[str]:
    yield t
    if t in forms:
        yield forms[t]
    yield simplemma.lemmatize(t, lang="en")
    if t.endswith("'s"):
        yield t[:-2]
    elif t.endswith("s'"):
        yield t[:-1]
    if "-" in t:
        yield from t.split("-")


class Translator:
    def __init__(self, dictionary: Dictionary) -> None:
        self.dictionary = dictionary
        self.lookup = lru_cache(maxsize=50_000)(self._lookup)

    def _lookup(self, t: str) -> tuple[str, str, list[Sense]] | None:
        """Return (key, lemma, senses); first candidate found wins. t must be lowercase.

        If the exact form has its own entry but is also an inflection of another
        headword (running -> run), the base word's senses are appended after it.
        """
        for cand in candidates(t, self.dictionary.forms):
            senses = self.dictionary.find(cand)
            if not senses:
                continue
            if cand == t:
                base = self._base_form(t)
                if base:
                    return t, base[0], senses + base[1]
            return cand, cand, senses
        return None

    def _base_form(self, t: str) -> tuple[str, list[Sense]] | None:
        for base in (self.dictionary.forms.get(t), simplemma.lemmatize(t, lang="en")):
            if base and base != t and (senses := self.dictionary.find(base)):
                return base, senses
        return None

    def translate(self, text: str) -> dict:
        segments: list[Segment] = []
        lexicon: dict[str, dict] = {}
        words = not_found = 0
        seen: set[str] = set()
        for is_word, s in tokenize(text):
            if not is_word or (len(s) == 1 and s.lower() not in SINGLE_LETTER_WORDS):
                append_text(segments, s)
                continue
            words += 1
            seg = self._word_segment(s, at_sentence_start(segments), lexicon)
            if seg["k"] is None:
                not_found += 1
            seen.add(s.lower())
            segments.append(seg)
        return {"segments": segments, "lexicon": lexicon,
                "stats": {"words": words, "unique": len(seen), "not_found": not_found}}

    def _word_segment(self, s: str, sentence_start: bool, lexicon: dict[str, dict]) -> Segment:
        t = s.lower().replace("\u2019", "'")
        seg: Segment = {"t": "w", "s": s, "k": None}
        hit = self.lookup(t)
        if hit is None and (parts := split_contraction(t)):
            hit = self.lookup(parts[0])
            if hit and parts[1]:
                seg["neg"] = True
        if hit:
            key, lemma, senses = hit
            seg["k"] = key
            lexicon.setdefault(key, {"lemma": lemma, "senses": senses})
        elif is_proper_noun(s, sentence_start):
            seg["pn"] = True
        return seg


def append_text(segments: list[Segment], s: str) -> None:
    if segments and segments[-1]["t"] == "x":
        segments[-1]["s"] += s
    else:
        segments.append({"t": "x", "s": s})


def at_sentence_start(segments: list[Segment]) -> bool:
    for seg in reversed(segments):
        if seg["t"] == "w":
            return False
        stripped = seg["s"].rstrip(" \t")
        if stripped:
            return stripped[-1] in SENTENCE_END
    return True


def is_proper_noun(s: str, sentence_start: bool) -> bool:
    return (len(s) > 1 and s.isupper()) or (s[0].isupper() and not sentence_start)
