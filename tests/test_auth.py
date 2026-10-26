import sqlite3

import pytest

from app import auth, db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCE_DB_DIR", raising=False)
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "finance.db")
    return tmp_path


def test_password_is_hashed_salted_and_verifiable():
    h1, h2 = auth.hash_password("correct horse"), auth.hash_password("correct horse")
    assert h1 != h2 and "correct horse" not in h1 and h1.startswith("scrypt$")      # random salt, never plain text
    assert auth.verify_password("correct horse", h1) and not auth.verify_password("wrong", h1)
    assert not auth.verify_password("x", "garbage") and not auth.verify_password("x", "scrypt$1$2$3$zz$yy")   # malformed hashes fail closed


def test_signup_then_login_roundtrip_and_email_is_case_insensitive():
    u, err = auth.create_user("  Asha@Example.com ", "s3cret-pass", "s3cret-pass")
    assert err is None and u["email"] == "asha@example.com" and len(u["id"]) == 32
    ok, err = auth.authenticate("ASHA@example.com", "s3cret-pass")
    assert err is None and ok["id"] == u["id"]


def test_database_stores_no_plaintext_password():
    auth.create_user("a@b.co", "s3cret-pass")
    con = sqlite3.connect(auth.users_db_path())
    dump = str(con.execute("SELECT * FROM users").fetchall())
    con.close()
    assert "s3cret-pass" not in dump


@pytest.mark.parametrize("email,pw,confirm,needle", [
    ("not-an-email", "s3cret-pass", None, "valid email"), ("", "s3cret-pass", None, "valid email"),
    ("a@b.co", "short", None, "at least 8"), ("a@b.co", "x" * 129, None, "at most"), ("a@b.co", "password", None, "too common"),
    ("a@b.co", "s3cret-pass", "different", "do not match")])
def test_signup_validation(email, pw, confirm, needle):
    u, err = auth.create_user(email, pw, confirm)
    assert u is None and needle in err


def test_duplicate_email_rejected():
    assert auth.create_user("a@b.co", "s3cret-pass")[1] is None
    u, err = auth.create_user("A@B.co", "another-pass1")
    assert u is None and "already exists" in err


def test_wrong_password_and_unknown_email_give_the_same_message():
    auth.create_user("a@b.co", "s3cret-pass")
    assert auth.authenticate("a@b.co", "nope-nope")[1] == auth.BAD_LOGIN
    assert auth.authenticate("ghost@b.co", "nope-nope")[1] == auth.BAD_LOGIN         # does not reveal which emails exist
    assert auth.authenticate("", "")[1] == auth.BAD_LOGIN and auth.authenticate("a@b.co", "x" * 5000)[1] == auth.BAD_LOGIN


def test_lockout_after_repeated_failures_and_recovery():
    auth.create_user("a@b.co", "s3cret-pass")
    for _ in range(auth.MAX_FAILS):
        assert auth.authenticate("a@b.co", "bad-guess1", now=1000.0)[1] == auth.BAD_LOGIN
    u, err = auth.authenticate("a@b.co", "s3cret-pass", now=1001.0)                  # even the right password is refused while locked
    assert u is None and "Too many attempts" in err
    u, err = auth.authenticate("a@b.co", "s3cret-pass", now=1000.0 + auth.LOCK_SECONDS + 1)
    assert err is None and u["email"] == "a@b.co"
    for _ in range(auth.MAX_FAILS - 1):                                              # counter was reset by the success
        auth.authenticate("a@b.co", "bad-guess1", now=5000.0)
    assert auth.authenticate("a@b.co", "s3cret-pass", now=5001.0)[1] is None


def test_each_user_gets_their_own_data_file_and_delete_removes_it():
    a, _ = auth.create_user("a@b.co", "s3cret-pass")
    b, _ = auth.create_user("b@b.co", "s3cret-pass")
    pa, pb = db.account_path(a["id"]), db.account_path(b["id"])
    assert pa != pb and pa.parent.name == "accounts"
    db.save_budgets({"Fuel": 100}, pa)
    assert db.load_budgets(pb) == {}
    assert auth.delete_user(a["id"]) and not pa.exists()
    assert auth.authenticate("a@b.co", "s3cret-pass")[0] is None
    assert auth.authenticate("b@b.co", "s3cret-pass")[0] is not None                  # other account untouched
    assert not auth.delete_user(a["id"])


def test_account_path_cannot_escape_its_folder():
    assert db.account_path("../../etc/passwd" + "ab12").parent.name == "accounts"
    with pytest.raises(ValueError):
        db.account_path("../..")
