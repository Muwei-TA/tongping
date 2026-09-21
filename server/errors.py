from datetime import datetime, timezone
from uuid import uuid4


class DomainError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def require(condition, status, code, message):
    if not condition:
        raise DomainError(status, code, message)


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid4().hex


def audit(db, club_id, actor, action, target):
    db.execute("INSERT INTO audit(club_id,actor_id,action,target_id,created_at) VALUES(?,?,?,?,?)",
               (club_id, actor, action, target, now()))
