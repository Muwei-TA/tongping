"""Fictional demo fixtures; never run implicitly on a production database."""
from datetime import datetime, timedelta, timezone
from .db import transaction
from .errors import now

PERSONAS = {"owner": "陈序", "member": "林杳", "next": "周周", "applicant": "新同学", "outsider": "夏禾"}


def seed(db):
    with transaction(db):
        if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return
        db.execute("INSERT INTO meta VALUES('mode','demo')")
        db.executemany("INSERT INTO users VALUES(?,?,?,?)",
                       [("u-" + key, "demo", key, name) for key, name in PERSONAS.items()])
        rules = "尊重原创；未经同意不外传；反馈针对作品，不评价人格。"
        db.executemany("INSERT INTO clubs VALUES(?,?,?,?,?)", [
            ("animation", "动画研习社", "带上你的半成品，这里有人愿意看。", rules, "u-owner"),
            ("photo", "光影摄影社", "一起发现校园里的日常。", rules, "u-outsider")])
        db.executemany("INSERT INTO memberships VALUES(?,?,?,?)", [
            ("animation", "u-" + key, "active", "演示成员") for key in ("owner", "member", "next")]
            + [("photo", "u-outsider", "active", "演示成员")])
        db.executemany("""INSERT INTO posts
            (id,club_id,author_id,client_id,kind,title,body,feedback,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", [
            ("forest", "animation", "u-member", "seed-forest", "work", "第一次做场景：森林里的慢镜头",
             "想做一个让人愿意停下来看的地方。用几何形体搭了这片森林，角色还没有开始走路。\n这次先不追求完成度，想听听大家对镜头和层次的建议。",
             "前景是不是太重了？视线能不能自然落到小人身上？", "approved", now()),
            ("notes", "animation", "u-owner", "seed-notes", "knowledge", "分镜自查清单：每个镜头只做一件事",
             "先写下镜头目的，再画画面。\n1. 我想让观众看到什么？\n2. 下一镜头改变了什么？\n3. 角色的行动能否替代解释？\n维护人：陈序。版本：1。", "欢迎补充你的制作经验。", "approved", now())])
        start = datetime.now(timezone.utc) + timedelta(days=7)
        db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)", (
            "screening", "animation", "带上你的半成品", "周五放映局。不完美，也值得登场。", "艺术楼 B201 · 演示地点",
            start.isoformat(), (start + timedelta(hours=2)).isoformat(), 2, "open"))
