"""Private publishing and review. No request or framework objects here."""
from .clubs import require_member, require_owner
from .db import transaction
from .errors import audit, new_id, now, require

POST_SELECT = "SELECT p.*,u.name AS author_name FROM posts p JOIN users u ON u.id=p.author_id"


def page(rows, limit, offset):
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


def get_post(db, post_id, actor):
    row = db.execute(POST_SELECT + " WHERE p.id=?", (post_id,)).fetchone()
    require(row is not None, 404, "NOT_FOUND", "内容不存在")
    club = require_member(db, row["club_id"], actor)
    visible = row["status"] == "approved" or actor in (row["author_id"], club["owner_id"])
    require(visible, 404, "NOT_FOUND", "内容不存在或尚未公开给社团")
    return dict(row)


def list_posts(db, club_id, actor, kind, query, mine, status, limit, offset):
    require_member(db, club_id, actor)
    conditions, values = ["p.club_id=?"], [club_id]
    if mine:
        conditions.append("p.author_id=?")
        values.append(actor)
    elif status:
        require_owner(db, club_id, actor)
    else:
        conditions.append("p.status='approved'")
    if status:
        conditions.append("p.status=?")
        values.append(status)
    if kind:
        conditions.append("p.kind=?")
        values.append(kind)
    if query:
        # instr is literal substring matching; %, _, and quotes are not query syntax.
        conditions.append("(instr(p.title,?)>0 OR instr(p.body,?)>0)")
        values.extend([query, query])
    sql = POST_SELECT + " WHERE " + " AND ".join(conditions) + " ORDER BY p.created_at DESC,p.id DESC LIMIT ? OFFSET ?"
    return page(db.execute(sql, (*values, limit, offset)), limit, offset)


def create_post(db, club_id, actor, data):
    fields = data.model_dump()
    with transaction(db):
        require_member(db, club_id, actor)
        old = db.execute("SELECT * FROM posts WHERE author_id=? AND client_id=?", (actor, data.client_id)).fetchone()
        if old:
            same = old["club_id"] == club_id and all(old[key] == value for key, value in fields.items())
            require(same, 409, "INTENT_CONFLICT", "同一发布请求不能更换内容，请创建新的发布请求")
            return get_post(db, old["id"], actor)
        if data.media_id:
            media = db.execute("SELECT club_id,author_id FROM media WHERE id=?", (data.media_id,)).fetchone()
            require(media is not None and media["club_id"] == club_id and media["author_id"] == actor,
                    422, "INVALID_MEDIA", "仅可关联本人在本社团上传的图片")
            require(not db.execute("SELECT 1 FROM posts WHERE media_id=?", (data.media_id,)).fetchone(),
                    409, "MEDIA_ATTACHED", "图片已经用于另一篇内容")
        pid = new_id()
        db.execute("""INSERT INTO posts(id,club_id,author_id,client_id,kind,title,body,feedback,media_id,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,'pending',?)""", (pid, club_id, actor, data.client_id, data.kind,
                       data.title, data.body, data.feedback, data.media_id, now()))
        audit(db, club_id, actor, "post.submit", pid)
        return get_post(db, pid, actor)


def review_post(db, post_id, actor, data):
    with transaction(db):
        post = get_post(db, post_id, actor)
        require_owner(db, post["club_id"], actor)
        require(post["status"] == "pending", 409, "ALREADY_REVIEWED", "内容已处理，请刷新")
        db.execute("UPDATE posts SET status=?,reason=? WHERE id=?", (data.status, data.reason, post_id))
        audit(db, post["club_id"], actor, "post." + data.status, post_id)
        return get_post(db, post_id, actor)


def list_comments(db, post_id, actor, limit, offset):
    post = get_post(db, post_id, actor)
    club = require_member(db, post["club_id"], actor)
    rows = db.execute("""SELECT c.*,u.name AS author_name FROM comments c JOIN users u ON u.id=c.author_id
        WHERE c.post_id=? AND (c.status='approved' OR c.author_id=? OR ?=?)
        ORDER BY c.created_at,c.id LIMIT ? OFFSET ?""", (post_id, actor, actor, club["owner_id"], limit, offset))
    return page(rows, limit, offset)


def create_comment(db, post_id, actor, body):
    with transaction(db):
        post = get_post(db, post_id, actor)
        require(post["status"] == "approved", 409, "NOT_PUBLISHED", "内容通过审核后才能反馈")
        cid = new_id()
        db.execute("INSERT INTO comments(id,post_id,author_id,body,status,created_at) VALUES(?,?,?,?,'pending',?)",
                   (cid, post_id, actor, body, now()))
        audit(db, post["club_id"], actor, "comment.submit", cid)
        return dict(db.execute("SELECT * FROM comments WHERE id=?", (cid,)).fetchone())


def review_comment(db, comment_id, actor, data):
    with transaction(db):
        comment = db.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
        require(comment is not None, 404, "NOT_FOUND", "反馈不存在")
        post = get_post(db, comment["post_id"], actor)
        require_owner(db, post["club_id"], actor)
        require(comment["status"] == "pending", 409, "ALREADY_REVIEWED", "反馈已处理，请刷新")
        db.execute("UPDATE comments SET status=?,reason=? WHERE id=?", (data.status, data.reason, comment_id))
        audit(db, post["club_id"], actor, "comment." + data.status, comment_id)
        return dict(db.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone())


def pending_comments(db, club_id, actor, limit, offset):
    require_owner(db, club_id, actor)
    rows = db.execute("""SELECT c.*,u.name AS author_name,p.title AS post_title
        FROM comments c JOIN posts p ON p.id=c.post_id JOIN users u ON u.id=c.author_id
        WHERE p.club_id=? AND c.status='pending' ORDER BY c.created_at,c.id LIMIT ? OFFSET ?""", (club_id, limit, offset))
    return page(rows, limit, offset)
