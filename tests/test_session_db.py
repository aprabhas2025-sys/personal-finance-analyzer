import os
import time

import pandas as pd
import pytest

from app import config, db


def _df(tag):
    return pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]), "description": [tag], "amount": [1.0], "type": ["debit"],
                         "category": ["Fuel"], "confidence": [1.0], "category_source": ["existing"]})


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCE_DB_DIR", raising=False)
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "finance.db")
    return tmp_path / "sessions"


def test_two_sessions_do_not_share_data(sessions):
    a, b = db.session_path("aaaa1111"), db.session_path("bbbb2222")
    assert a != b and a.parent == sessions
    db.replace_all(_df("ALICE"), a)
    db.replace_all(_df("BOB"), b)
    assert list(db.load(a)["description"]) == ["ALICE"] and list(db.load(b)["description"]) == ["BOB"]
    db.clear(a)
    assert db.load(a).empty and list(db.load(b)["description"]) == ["BOB"]        # clearing one session leaves the other


def test_session_id_cannot_escape_the_folder(sessions):
    p = db.session_path("../../etc/passwd" + "ab12")
    assert p.parent == sessions and p.name.endswith(".db") and "/" not in p.name and ".." not in p.name
    with pytest.raises(ValueError):
        db.session_path("../../")


def test_db_dir_env_overrides_location(sessions, tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DB_DIR", str(tmp_path / "elsewhere"))
    assert db.session_path("ab12").parent == tmp_path / "elsewhere"


def test_purge_old_removes_only_stale_sessions(sessions):
    old, fresh = db.session_path("0ld0"), db.session_path("fe5e")
    db.replace_all(_df("x"), old)
    db.replace_all(_df("y"), fresh)
    two_days_ago = time.time() - 48 * 3600
    os.utime(old, (two_days_ago, two_days_ago))
    assert db.purge_old(24) == 1
    assert not old.exists() and fresh.exists()
    assert db.purge_old(24, folder=sessions / "missing") == 0


@pytest.mark.parametrize("env,expected", [({"RENDER": "true"}, True), ({"FINANCE_HOSTED": "1"}, True),
                                          ({"FINANCE_HOSTED": "0"}, False), ({}, False)])
def test_hosted_flag(monkeypatch, env, expected):
    for k in ("RENDER", "FINANCE_HOSTED"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert config.is_hosted() is expected


def test_captions_do_not_make_false_privacy_claims():
    assert "never leaves this machine" in config.LOCAL_CAPTION
    assert "never leaves" not in config.HOSTED_CAPTION and "hosted" in config.HOSTED_CAPTION


def test_every_db_call_closes_its_connection(sessions, monkeypatch):
    """An open handle makes unlink() fail on Windows, which would silently break purge_old. Platform-independent check."""
    import sqlite3
    opened = []
    real = sqlite3.connect

    class Tracked:
        def __init__(self, *a, **k):
            self.c, self.closed = real(*a, **k), False
            opened.append(self)

        def __getattr__(self, n):
            return getattr(self.c, n)

        def close(self):
            self.closed = True
            self.c.close()

    monkeypatch.setattr(db.sqlite3, "connect", Tracked)
    p = db.session_path("c10c")
    db.replace_all(_df("x"), p)
    db.load(p), db.count(p)
    db.update_category([1], "Health", p)
    db.apply_predictions(pd.DataFrame({"id": [1], "category": ["Fuel"], "confidence": [0.5], "category_source": ["ml"]}), p)
    db.clear(p)
    assert opened and all(t.closed for t in opened)
    n = len(opened)
    bad = _df("y").assign(type="not-a-valid-type")                               # violates the CHECK constraint
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_all(bad, p)
    assert len(opened) > n and all(t.closed for t in opened)                     # a failing call still closes
