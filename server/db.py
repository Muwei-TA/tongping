"""Connection and transaction lifecycle only; no product policy."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3


def connect(path):
    db = sqlite3.connect(str(path), timeout=10, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing_connection(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            db.executescript(Path(__file__).with_name("schema.sql").read_text())
        elif version != 1:
            raise RuntimeError(f"Unsupported database version: {version}")


@contextmanager
def closing_connection(path):
    db = connect(path)
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
