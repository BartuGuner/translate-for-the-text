from __future__ import annotations


def test_health(client) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok" and res.get_json()["entries"] > 10_000


def test_index_served(client) -> None:
    res = client.get("/")
    assert res.status_code == 200 and b"LexiHover" in res.data
    assert "utf-8" in res.headers["Content-Type"].lower()


def test_translate_happy_path(client) -> None:
    text = "Running fast, books\nand Zorblaxqy."
    res = client.post("/api/translate", json={"text": text})
    assert res.status_code == 200
    data = res.get_json()
    assert "".join(s["s"] for s in data["segments"]) == text
    lemma = {s["s"]: data["lexicon"][s["k"]]["lemma"] if s["k"] else None
             for s in data["segments"] if s["t"] == "w"}
    assert lemma["Running"] == "run" and lemma["books"] == "book" and lemma["Zorblaxqy"] is None
    assert data["lexicon"]["book"]["senses"][0]["tr"]
    assert data["stats"]["not_found"] == 1


def test_translate_empty(client) -> None:
    for text in ("", "   \n"):
        res = client.post("/api/translate", json={"text": text})
        assert res.status_code == 400 and res.get_json()["error"] == "text_empty"


def test_translate_too_long(client) -> None:
    res = client.post("/api/translate", json={"text": "a" * 50_001})
    assert res.status_code == 400 and res.get_json()["error"] == "text_too_long"


def test_translate_bad_request(client) -> None:
    assert client.post("/api/translate", data="nope").get_json()["error"] == "bad_request"
    assert client.post("/api/translate", json={"text": 5}).status_code == 400


def test_repeated_words_once_in_lexicon(client) -> None:
    data = client.post("/api/translate", json={"text": "book books Book book"}).get_json()
    assert list(data["lexicon"]) == ["book"]
    assert all(s["k"] == "book" for s in data["segments"] if s["t"] == "w")


def test_turkish_characters_not_escaped(client) -> None:
    res = client.post("/api/translate", json={"text": "dictionary"})
    assert "sözlük".encode() in res.data
