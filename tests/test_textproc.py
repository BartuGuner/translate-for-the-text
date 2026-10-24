from __future__ import annotations

import pytest

from app.textproc import tokenize


@pytest.mark.parametrize("text", [
    "",
    "Hello, world! How are you?",
    "Line one.\n\nLine two\r\n\tindented   spaces  ",
    "I love pizza 🍕 and 🎉 parties!",
    "Don't stop; it's John's dog and the dogs' bowls — rock\u2019n\u2019roll.",
    "A well-known state-of-the-art idea -- not -dash- here.",
    "In 2024 we sold 3.5 million units (42%).",
    "   ",
    "ünïcödé çağ ışık",
])
def test_tokenize_roundtrip(text: str) -> None:
    assert "".join(s for _, s in tokenize(text)) == text


def test_tokenize_words() -> None:
    words = [s for is_word, s in tokenize("Don't stop the well-known rock\u2019n\u2019roll 42 times.") if is_word]
    assert words == ["Don't", "stop", "the", "well-known", "rock\u2019n\u2019roll", "times"]


def lex(translator, word: str) -> str | None:
    hit = translator.lookup(word.lower())
    return hit[1] if hit else None


def test_exact(translator) -> None:
    assert lex(translator, "house") == "house"
    assert lex(translator, "water") == "water"


@pytest.mark.parametrize("word,lemma", [("running", "run"), ("books", "book"), ("studies", "study")])
def test_lemma(translator, word: str, lemma: str) -> None:
    assert lex(translator, word) == lemma


@pytest.mark.parametrize("word,lemma", [("went", "go"), ("children", "child")])
def test_irregular(translator, word: str, lemma: str) -> None:
    assert lex(translator, word) == lemma


def test_possessive(translator) -> None:
    result = translator.translate("The teacher's book.")
    seg = [s for s in result["segments"] if s["s"] == "teacher's"][0]
    assert seg["k"] == "teacher"


def test_hyphenated(translator) -> None:
    seg = [s for s in translator.translate("a sun-water day")["segments"] if s["s"] == "sun-water"][0]
    assert seg["k"] in {"sun", "water"}


def test_not_found(translator) -> None:
    seg = translator.translate("the zorblaxqy is here")["segments"][2]
    assert seg["k"] is None and "pn" not in seg


def test_proper_noun(translator) -> None:
    segs = translator.translate("I met Zorblaxqy yesterday. NASAQX too.")["segments"]
    by_s = {s["s"]: s for s in segs if s["t"] == "w"}
    assert by_s["Zorblaxqy"]["pn"] and by_s["Zorblaxqy"]["k"] is None
    assert by_s["NASAQX"]["pn"]


def test_sentence_start_capital(translator) -> None:
    seg = translator.translate("Water is good.")["segments"][0]
    assert seg["k"] == "water"


def test_contraction_negative(translator) -> None:
    result = translator.translate("we don't know")
    seg = result["segments"][2]
    assert result["lexicon"][seg["k"]]["lemma"] in {"do", "don't"}


def test_numbers_and_single_letters_are_plain(translator) -> None:
    result = translator.translate("Item 42 b x")
    assert [s["s"] for s in result["segments"] if s["t"] == "w"] == ["Item"]


def test_repeats_counted_once(translator) -> None:
    stats = translator.translate("Book book BOOK books.")["stats"]
    assert stats["words"] == 4 and stats["unique"] == 2
