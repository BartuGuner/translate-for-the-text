from __future__ import annotations

import csv
import io

from app.favorites import Favorites

FAV = {"word": "Books", "lemma": "book", "pos": "noun", "meanings": ["kitap", "defter"],
       "context": "Books are great."}


def test_add_and_list(client) -> None:
    res = client.post("/api/favorites", json=FAV)
    assert res.status_code == 201
    row = res.get_json()
    assert row["lemma"] == "book" and row["meanings"] == ["kitap", "defter"] and row["added_at"]
    assert [f["lemma"] for f in client.get("/api/favorites").get_json()] == ["book"]


def test_duplicate_lemma(client) -> None:
    first = client.post("/api/favorites", json=FAV).get_json()
    res = client.post("/api/favorites", json={**FAV, "word": "book", "meanings": ["x"]})
    assert res.status_code == 200 and res.get_json()["id"] == first["id"]
    assert len(client.get("/api/favorites").get_json()) == 1


def test_search(client) -> None:
    client.post("/api/favorites", json=FAV)
    client.post("/api/favorites", json={**FAV, "word": "water", "lemma": "water", "meanings": ["su"]})
    assert [f["lemma"] for f in client.get("/api/favorites?q=wat").get_json()] == ["water"]
    assert [f["lemma"] for f in client.get("/api/favorites?q=kitap").get_json()] == ["book"]


def test_delete(client) -> None:
    fav_id = client.post("/api/favorites", json=FAV).get_json()["id"]
    assert client.delete(f"/api/favorites/{fav_id}").status_code == 204
    assert client.get("/api/favorites").get_json() == []
    assert client.delete(f"/api/favorites/{fav_id}").status_code == 404


def test_bad_payload(client) -> None:
    assert client.post("/api/favorites", json={"word": "x"}).status_code == 400
    assert client.post("/api/favorites", json={**FAV, "meanings": "kitap"}).status_code == 400


def test_csv_export_turkish(client) -> None:
    client.post("/api/favorites", json={**FAV, "meanings": ["çağ", "ışık", "göğüs", "şüphe"]})
    res = client.get("/api/favorites/export.csv")
    assert res.status_code == 200 and "text/csv" in res.headers["Content-Type"]
    assert res.data.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(res.data.decode("utf-8-sig"))))
    assert rows[0] == ["word", "lemma", "pos", "meanings", "context", "added_at"]
    assert rows[1][3] == "çağ; ışık; göğüs; şüphe"


def test_context_truncated_and_db_created_lazily(tmp_path) -> None:
    db = tmp_path / "sub" / "user.db"
    favs = Favorites(db)
    assert favs.list() == []
    row, created = favs.add("x", "x", None, [], "a" * 500)
    assert created and len(row["context"]) == 300 and db.exists()
