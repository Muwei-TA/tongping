"""Provider-scoped accounts and revocable opaque sessions."""
import hashlib
import os
import secrets
import time
import httpx
from .db import transaction
from .errors import DomainError, new_id, require
from .seed import PERSONAS

PROVIDERS = {
    "wechat": ("WECHAT", "https://api.weixin.qq.com/sns/jscode2session"),
    "qq": ("QQ", "https://api.q.qq.com/sns/jscode2session"),
}


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db, user_id):
    token = secrets.token_urlsafe(32)
    expires = time.time() + 8 * 3600
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
    db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), user_id, expires))
    user = dict(db.execute("SELECT id,name FROM users WHERE id=?", (user_id,)).fetchone())
    return {"token": token, "expires_at": expires, "user": user}


def demo_login(db, persona, enabled):
    require(enabled, 404, "NOT_FOUND", "演示登录未开启")
    require(persona in PERSONAS, 422, "VALIDATION_ERROR", "未知演示身份")
    with transaction(db):
        return issue_session(db, "u-" + persona)


def authenticate(db, authorization):
    require(bool(authorization) and authorization.startswith("Bearer "), 401, "UNAUTHENTICATED", "请先登录")
    token = authorization[7:]
    user = db.execute("""SELECT u.id,u.name FROM sessions s JOIN users u ON u.id=s.user_id
                         WHERE s.token_hash=? AND s.expires_at>?""", (token_hash(token), time.time())).fetchone()
    require(user is not None, 401, "UNAUTHENTICATED", "登录已过期，请重新登录")
    return dict(user)


def logout(db, authorization):
    db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(authorization[7:]),))


def exchange_code(provider, code):
    prefix, endpoint = PROVIDERS[provider]
    appid, secret = os.getenv(prefix + "_APP_ID"), os.getenv(prefix + "_APP_SECRET")
    require(bool(appid and secret), 503, "PROVIDER_NOT_CONFIGURED", "尚未配置宿主登录凭据")
    try:
        response = httpx.get(endpoint, params={"appid": appid, "secret": secret,
                            "js_code": code, "grant_type": "authorization_code"}, timeout=10)
        response.raise_for_status()
        value = response.json()
    except (httpx.HTTPError, ValueError):
        raise DomainError(502, "PROVIDER_UNAVAILABLE", "宿主登录服务暂不可用") from None
    valid = isinstance(value, dict) and isinstance(value.get("openid"), str) and 0 < len(value["openid"]) <= 256
    require(valid and value.get("errcode", 0) == 0, 401, "PROVIDER_REJECTED", "登录凭证无效，请重新授权")
    return value["openid"]


def code_login(db, provider, code):
    subject = exchange_code(provider, code)
    with transaction(db):
        user = db.execute("SELECT id FROM users WHERE provider=? AND subject=?", (provider, subject)).fetchone()
        uid = user["id"] if user else new_id()
        if user is None:
            db.execute("INSERT INTO users VALUES(?,?,?,?)", (uid, provider, subject, "新同学"))
        return issue_session(db, uid)
