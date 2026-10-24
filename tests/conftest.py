from __future__ import annotations

import pytest

from app import config
from app.dictionary import Dictionary
from app.main import create_app
from app.textproc import Translator


@pytest.fixture(scope="session")
def dictionary() -> Dictionary:
    if not config.DICTIONARY_DB.exists():
        pytest.skip("data/dictionary.db missing; run tools/build_dictionary.py")
    return Dictionary(config.DICTIONARY_DB)


@pytest.fixture(scope="session")
def translator(dictionary: Dictionary) -> Translator:
    return Translator(dictionary)


@pytest.fixture()
def client(tmp_path, dictionary):
    app = create_app(user_db=tmp_path / "user.db")
    app.config["TESTING"] = True
    return app.test_client()
