from typing import Annotated
import sqlite3
from fastapi import Depends, Header, Request
from .db import closing_connection
from .identity import authenticate


def database(request: Request):
    with closing_connection(request.app.state.db_path) as connection:
        yield connection


Database = Annotated[sqlite3.Connection, Depends(database)]
Authorization = Annotated[str | None, Header()]


def current_user(db: Database, authorization: Authorization = None):
    return authenticate(db, authorization)


User = Annotated[dict, Depends(current_user)]
