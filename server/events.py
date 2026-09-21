"""Seat allocation and FIFO waitlists are one SQLite write transaction."""
from datetime import datetime, timezone
from .clubs import require_member, require_owner
from .content import page
from .db import transaction
from .errors import audit, new_id, now, require


def get_event(db, event_id, actor):
    row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    require(row is not None, 404, "NOT_FOUND", "活动不存在")
    require_member(db, row["club_id"], actor)
    counts = dict(db.execute("SELECT status,count(*) FROM registrations WHERE event_id=? GROUP BY status", (event_id,)))
    own = db.execute("SELECT status FROM registrations WHERE event_id=? AND user_id=?", (event_id, actor)).fetchone()
    return {**dict(row), "confirmed": counts.get("confirmed", 0), "waiting": counts.get("waiting", 0),
            "my_registration": own["status"] if own else None}


def list_events(db, club_id, actor, limit, offset):
    require_member(db, club_id, actor)
    ids = db.execute("SELECT id FROM events WHERE club_id=? ORDER BY starts_at,id LIMIT ? OFFSET ?", (club_id, limit, offset)).fetchall()
    return {"items": [get_event(db, row[0], actor) for row in ids], "limit": limit, "offset": offset}


def create_event(db, club_id, actor, data):
    with transaction(db):
        require_owner(db, club_id, actor)
        eid = new_id()
        db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,'open')", (eid, club_id, data.title,
            data.description, data.location, data.starts_at.isoformat(), data.ends_at.isoformat(), data.capacity))
        audit(db, club_id, actor, "event.create", eid)
        return get_event(db, eid, actor)


def registration_open(event):
    require(event["status"] == "open", 409, "EVENT_CANCELLED", "活动已取消")
    require(datetime.fromisoformat(event["starts_at"]) > datetime.now(timezone.utc),
            409, "REGISTRATION_CLOSED", "活动已开始，报名和取消已关闭")


def register(db, event_id, actor):
    with transaction(db):
        event = get_event(db, event_id, actor)
        registration_open(event)
        if event["my_registration"] in ("confirmed", "waiting"):
            return {"status": event["my_registration"]}
        status = "confirmed" if event["confirmed"] < event["capacity"] else "waiting"
        db.execute("""INSERT INTO registrations VALUES(?,?,?,?) ON CONFLICT(event_id,user_id)
            DO UPDATE SET status=excluded.status,created_at=excluded.created_at""", (event_id, actor, status, now()))
        audit(db, event["club_id"], actor, "registration." + status, event_id)
        return {"status": status}


def cancel_registration(db, event_id, actor):
    with transaction(db):
        event = get_event(db, event_id, actor)
        if event["my_registration"] in (None, "cancelled"):
            return
        registration_open(event)
        db.execute("UPDATE registrations SET status='cancelled' WHERE event_id=? AND user_id=?", (event_id, actor))
        if event["my_registration"] == "confirmed":
            candidate = db.execute("""SELECT r.user_id FROM registrations r JOIN memberships m
                ON m.user_id=r.user_id AND m.club_id=? WHERE r.event_id=? AND r.status='waiting'
                AND m.status='active' ORDER BY r.created_at,r.user_id LIMIT 1""", (event["club_id"], event_id)).fetchone()
            if candidate:
                db.execute("UPDATE registrations SET status='confirmed' WHERE event_id=? AND user_id=?", (event_id, candidate[0]))
                audit(db, event["club_id"], actor, "registration.promote", candidate[0])
        audit(db, event["club_id"], actor, "registration.cancel", event_id)


def cancel_event(db, event_id, actor):
    with transaction(db):
        event = get_event(db, event_id, actor)
        require_owner(db, event["club_id"], actor)
        if event["status"] != "cancelled":
            db.execute("UPDATE events SET status='cancelled' WHERE id=?", (event_id,))
            db.execute("UPDATE registrations SET status='cancelled' WHERE event_id=?", (event_id,))
            audit(db, event["club_id"], actor, "event.cancel", event_id)
        return get_event(db, event_id, actor)
