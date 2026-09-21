"""Membership is checked at use time, never trusted from client roles."""
from .db import transaction
from .errors import require, audit


def get_club(db, club_id):
    row = db.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    require(row is not None, 404, "NOT_FOUND", "社团不存在")
    return dict(row)


def require_member(db, club_id, user_id):
    club = get_club(db, club_id)
    member = db.execute("SELECT status FROM memberships WHERE club_id=? AND user_id=?", (club_id, user_id)).fetchone()
    require(member is not None and member["status"] == "active", 403, "MEMBERSHIP_REQUIRED", "加入社团并通过审核后可访问")
    return club


def require_owner(db, club_id, user_id):
    club = require_member(db, club_id, user_id)
    require(club["owner_id"] == user_id, 403, "OWNER_REQUIRED", "仅当前社长可以操作")
    return club


def list_clubs(db, limit, offset):
    return {"items": [dict(r) for r in db.execute("SELECT * FROM clubs ORDER BY id LIMIT ? OFFSET ?", (limit, offset))],
            "limit": limit, "offset": offset}


def profile(db, user):
    memberships = [dict(r) for r in db.execute("""SELECT m.club_id,m.status,c.name,
        CASE WHEN c.owner_id=m.user_id THEN 'owner' ELSE 'member' END AS role
        FROM memberships m JOIN clubs c ON c.id=m.club_id WHERE m.user_id=? ORDER BY c.id""", (user["id"],))]
    return {**user, "memberships": memberships}


def apply(db, club_id, user_id, reason):
    with transaction(db):
        get_club(db, club_id)
        old = db.execute("SELECT status FROM memberships WHERE club_id=? AND user_id=?", (club_id, user_id)).fetchone()
        if old and old["status"] in ("active", "pending"):
            return dict(old)
        db.execute("""INSERT INTO memberships VALUES(?,?,'pending',?)
            ON CONFLICT(club_id,user_id) DO UPDATE SET status='pending',reason=excluded.reason""", (club_id, user_id, reason))
        audit(db, club_id, user_id, "membership.apply", user_id)
    return {"status": "pending"}


def members(db, club_id, actor, limit, offset):
    require_owner(db, club_id, actor)
    rows = db.execute("""SELECT m.user_id,u.name,m.status,m.reason FROM memberships m
        JOIN users u ON u.id=m.user_id WHERE m.club_id=? ORDER BY m.status,u.name LIMIT ? OFFSET ?""", (club_id, limit, offset))
    return {"items": [dict(r) for r in rows], "limit": limit, "offset": offset}


def review_member(db, club_id, actor, user_id, status):
    with transaction(db):
        require_owner(db, club_id, actor)
        row = db.execute("SELECT status FROM memberships WHERE club_id=? AND user_id=?", (club_id, user_id)).fetchone()
        require(row is not None, 404, "NOT_FOUND", "申请不存在")
        require(row["status"] == "pending", 409, "ALREADY_REVIEWED", "申请已处理，请刷新")
        db.execute("UPDATE memberships SET status=? WHERE club_id=? AND user_id=?", (status, club_id, user_id))
        audit(db, club_id, actor, "membership." + status, user_id)
    return {"status": status}
