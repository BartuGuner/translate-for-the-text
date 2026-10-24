"""Flask app factory and routes."""
from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from . import config
from .dictionary import Dictionary
from .favorites import Favorites
from .textproc import Translator

log = logging.getLogger("lexihover")
STATIC = Path(__file__).resolve().parent / "static"


def error(code: str, status: int = 400) -> tuple[Response, int]:
    return jsonify(error=code), status


def create_app(dictionary_db: Path = config.DICTIONARY_DB, user_db: Path = config.USER_DB) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BYTES
    app.json.ensure_ascii = False
    dictionary = Dictionary(dictionary_db)
    translator = Translator(dictionary)
    favorites = Favorites(user_db)

    @app.after_request
    def no_cache_api(resp: Response) -> Response:
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(413)
    def too_large(_e: Exception) -> tuple[Response, int]:
        return error("text_too_long")

    @app.get("/")
    def index() -> Response:
        return send_from_directory(STATIC, "index.html", mimetype="text/html")

    @app.get("/api/health")
    def health() -> Response:
        return jsonify(status="ok", entries=dictionary.entry_count())

    @app.post("/api/translate")
    def translate() -> Response | tuple[Response, int]:
        body = request.get_json(silent=True)
        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str):
            return error("bad_request")
        if not text.strip():
            return error("text_empty")
        if len(text) > config.MAX_TEXT_CHARS:
            return error("text_too_long")
        result = translator.translate(text)
        log.info("translate: %(words)d words, %(unique)d unique, %(not_found)d not found", result["stats"])
        return jsonify(result)

    @app.get("/api/favorites")
    def list_favorites() -> Response:
        return jsonify(favorites.list(request.args.get("q", "").strip()))

    @app.post("/api/favorites")
    def add_favorite() -> Response | tuple[Response, int]:
        body = request.get_json(silent=True)
        fav = parse_favorite(body)
        if fav is None:
            return error("bad_request")
        row, created = favorites.add(**fav)
        return jsonify(row), 201 if created else 200

    @app.delete("/api/favorites/<int:fav_id>")
    def delete_favorite(fav_id: int) -> tuple[str, int]:
        return "", 204 if favorites.delete(fav_id) else 404

    @app.get("/api/favorites/export.csv")
    def export_csv() -> Response:
        return Response(favorites.export_csv(), mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=lexihover-favorites.csv"})

    return app


def parse_favorite(body: object) -> dict | None:
    if not isinstance(body, dict):
        return None
    word, lemma, meanings = body.get("word"), body.get("lemma"), body.get("meanings")
    pos, context = body.get("pos"), body.get("context")
    if not (isinstance(word, str) and word and isinstance(lemma, str) and lemma):
        return None
    if not (isinstance(meanings, list) and all(isinstance(m, str) for m in meanings)):
        return None
    if pos is not None and not isinstance(pos, str) or context is not None and not isinstance(context, str):
        return None
    return {"word": word, "lemma": lemma.lower(), "pos": pos, "meanings": meanings, "context": context}


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if not config.DICTIONARY_DB.exists():
        raise SystemExit(f"Dictionary not found: {config.DICTIONARY_DB}")
    app = create_app()
    url = f"http://{config.HOST}:{config.PORT}/"
    print(f"LexiHover running at {url}  (press Ctrl+C to stop)")
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)


if __name__ == "__main__":
    run()
