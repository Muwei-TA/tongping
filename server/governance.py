"""Two-party handover; the club owner field is the only role authority."""
from datetime import datetime, timedelta, timezone
from .clubs import require_member, require_owner
from .content import page
from .db import transaction
from .errors import audit, new_id, now, require


def handovers(db, actor, limit, offset):
    rows = db.execute("""SELECT h.*,c.name AS club_name,u.name AS to_name FROM handovers h
        JOIN clubs c ON c.id=h.club_id JOIN users u ON u.id=h.to_user_id
        JOIN memberships m ON m.club_id=h.club_id AND m.user_id=? AND m.status='active'
        WHERE h.from_user_id=? OR h.to_user_id=? ORDER BY h.expires_at DESC,h.id LIMIT ? OFFSET ?""",
        (actor, actor, actor, limit, offset))
    return page(rows, limit, offset)


def start_handover(db, club_id, actor, to_user_id):
    with transaction(db):
        require_owner(db, club_id, actor)
        require(actor != to_user_id, 422, "INVALID_SUCCESSOR", "继任者不能是现任社长")
        require_member(db, club_id, to_user_id)
        db.execute("UPDATE handovers SET status='expired' WHERE club_id=? AND status='pending' AND expires_at<=?", (club_id, now()))
        pending = db.execute("SELECT * FROM handovers WHERE club_id=? AND status='pending'", (club_id,)).fetchone()
        if pending:
            require(pending["to_user_id"] == to_user_id, 409, "HANDOVER_PENDING", "已有待确认交接，48 小时后可重新发起")
            return dict(pending)
        hid = new_id()
        expires = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
        db.execute("INSERT INTO handovers VALUES(?,?,?,?,?,'pending')", (hid, club_id, actor, to_user_id, expires))
        audit(db, club_id, actor, "handover.start", hid)
        return dict(db.execute("SELECT * FROM handovers WHERE id=?", (hid,)).fetchone())


def accept_handover(db, handover_id, actor):
    with transaction(db):
        item = db.execute("SELECT * FROM handovers WHERE id=?", (handover_id,)).fetchone()
        require(item is not None, 404, "NOT_FOUND", "交接不存在")
        require(item["to_user_id"] == actor, 403, "SUCCESSOR_REQUIRED", "仅指定继任者可以确认")
        club = require_member(db, item["club_id"], actor)
        if item["status"] == "completed":
            return dict(item)
        require(item["status"] == "pending" and item["expires_at"] > now(), 409, "HANDOVER_EXPIRED", "交接已过期，请由现任社长重新发起")
        require(club["owner_id"] == item["from_user_id"], 409, "OWNER_CHANGED", "社长已变更，请重新发起交接")
        db.execute("UPDATE clubs SET owner_id=? WHERE id=?", (actor, item["club_id"]))
        db.execute("UPDATE handovers SET status='completed' WHERE id=?", (handover_id,))
        audit(db, item["club_id"], actor, "handover.accept", handover_id)
        return dict(db.execute("SELECT * FROM handovers WHERE id=?", (handover_id,)).fetchone())
