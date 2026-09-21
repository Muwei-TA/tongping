"""Contract tests use a fresh real SQLite database for each test."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
import sqlite3

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server.app import create_app

API = "/api/v1"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite", demo=True)) as value:
        yield value


def login(client, persona="member"):
    response = client.post(API + "/auth/demo", json={"persona": persona})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def post_input(client_id="intent-1", **changes):
    return {"client_id": client_id, "kind": "work", "title": "森林里的新镜头",
            "body": "我想改善镜头节奏。", "feedback": "前景是否太重？", **changes}


def new_post(client, headers=None, **changes):
    headers = headers or login(client)
    response = client.post(API + "/clubs/animation/posts", headers=headers,
                           json=post_input(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_private_detail_requires_login(client):
    response = client.get(API + "/posts/forest")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_public_club_does_not_include_members_or_posts(client):
    response = client.get(API + "/clubs/animation")
    assert response.status_code == 200
    assert "members" not in response.json()
    assert "posts" not in response.json()


def test_demo_is_off_by_default(tmp_path):
    with TestClient(create_app(tmp_path / "prod.sqlite")) as client:
        assert client.post(API + "/auth/demo", json={"persona": "owner"}).status_code == 404


def test_production_rejects_demo(tmp_path):
    with pytest.raises(ValueError):
        create_app(tmp_path / "prod.sqlite", demo=True, production=True)


def test_real_login_never_falls_back_to_demo(client):
    response = client.post(API + "/auth/code", json={"provider": "wechat", "code": "bad"})
    assert response.status_code == 503
    assert "token" not in response.json()


def test_logout_revokes_session(client):
    headers = login(client)
    assert client.get(API + "/me", headers=headers).status_code == 200
    assert client.delete(API + "/auth/session", headers=headers).status_code == 204
    assert client.get(API + "/me", headers=headers).status_code == 401


def test_profile_never_exposes_provider_subject(client):
    response = client.get(API + "/me", headers=login(client))
    assert "subject" not in response.text
    assert "session_key" not in response.text


@pytest.mark.parametrize("path", ["/posts/forest", "/clubs/animation/posts", "/clubs/animation/events",
                                  "/clubs/animation/posts?q=森林", "/clubs/animation/members"])
def test_outsider_cannot_read_private_resources(client, path):
    response = client.get(API + path, headers=login(client, "outsider"))
    assert response.status_code in (403, 404)
    assert "森林里的慢镜头" not in response.text


def test_join_requires_review_and_rules_consent(client):
    applicant = login(client, "applicant")
    url = API + "/clubs/animation/membership"
    assert client.post(url, headers=applicant, json={"reason": "想学动画", "accept_rules": False}).status_code == 422
    response = client.post(url, headers=applicant, json={"reason": "想学动画", "accept_rules": True})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert client.get(API + "/posts/forest", headers=applicant).status_code == 403
    owner = login(client, "owner")
    result = client.patch(API + "/clubs/animation/members/u-applicant", headers=owner, json={"status": "active"})
    assert result.status_code == 200
    assert client.get(API + "/posts/forest", headers=applicant).status_code == 200


def test_member_cannot_approve_or_enumerate_roster(client):
    headers = login(client)
    assert client.get(API + "/clubs/animation/members", headers=headers).status_code == 403
    result = client.patch(API + "/clubs/animation/members/u-applicant", headers=headers, json={"status": "active"})
    assert result.status_code == 403


def test_pending_post_hidden_until_approval(client):
    author = login(client)
    item = new_post(client, author)
    assert item["status"] == "pending"
    peer = login(client, "next")
    assert client.get(API + "/posts/" + item["id"], headers=peer).status_code == 404
    assert item["id"] not in [p["id"] for p in client.get(API + "/clubs/animation/posts", headers=peer).json()["items"]]
    response = client.patch(API + "/posts/" + item["id"] + "/review", headers=login(client, "owner"), json={"status": "approved", "reason": ""})
    assert response.status_code == 200
    assert client.get(API + "/posts/" + item["id"], headers=peer).status_code == 200


def test_post_idempotency_does_not_duplicate_and_rejects_changed_payload(client):
    headers = login(client)
    first = new_post(client, headers)
    second = new_post(client, headers)
    assert first["id"] == second["id"]
    changed = client.post(API + "/clubs/animation/posts", headers=headers, json=post_input(title="另一条作品"))
    assert changed.status_code == 409


@pytest.mark.parametrize("change", [{"title": " "}, {"body": ""}, {"kind": "admin"}, {"status": "approved"}, {"title": "长" * 101}])
def test_post_validates_at_boundary(client, change):
    response = client.post(API + "/clubs/animation/posts", headers=login(client), json=post_input(**change))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reject_requires_reason_and_cannot_review_twice(client):
    item = new_post(client)
    url = API + "/posts/" + item["id"] + "/review"
    owner = login(client, "owner")
    assert client.patch(url, headers=owner, json={"status": "rejected", "reason": ""}).status_code == 422
    assert client.patch(url, headers=owner, json={"status": "rejected", "reason": "请补充来源"}).status_code == 200
    assert client.patch(url, headers=owner, json={"status": "approved", "reason": ""}).status_code == 409


def test_comment_requires_review(client):
    author = login(client)
    response = client.post(API + "/posts/forest/comments", headers=author, json={"body": "试着压低前景的对比度。"})
    assert response.status_code == 201
    comment = response.json()
    peer = login(client, "next")
    assert comment["id"] not in [c["id"] for c in client.get(API + "/posts/forest/comments", headers=peer).json()["items"]]
    review = client.patch(API + "/comments/" + comment["id"] + "/review", headers=login(client, "owner"), json={"status": "approved", "reason": ""})
    assert review.status_code == 200
    assert comment["id"] in [c["id"] for c in client.get(API + "/posts/forest/comments", headers=peer).json()["items"]]


def test_search_scoped_and_paginated(client):
    response = client.get(API + "/clubs/animation/posts?kind=knowledge&limit=1&q=分镜", headers=login(client))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["kind"] == "knowledge"
    assert "photo" not in response.text
    assert client.get(API + "/clubs/animation/posts?limit=99999", headers=login(client)).status_code == 422


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (16, 16), "green").save(output, format="PNG")
    return output.getvalue()


def test_media_is_private_before_and_after_publication(client):
    author = login(client)
    response = client.post(API + "/clubs/animation/media", headers=author, files={"file": ("image.png", image_bytes(), "image/png")})
    assert response.status_code == 201
    mid = response.json()["id"]
    assert client.get(API + "/media/" + mid).status_code == 401
    assert client.get(API + "/media/" + mid, headers=login(client, "next")).status_code == 404
    item = new_post(client, author, media_id=mid)
    client.patch(API + "/posts/" + item["id"] + "/review", headers=login(client, "owner"), json={"status": "approved", "reason": ""})
    result = client.get(API + "/media/" + mid, headers=login(client, "next"))
    assert result.status_code == 200
    assert result.headers["content-type"] == "image/png"
    assert client.get(API + "/media/" + mid, headers=login(client, "outsider")).status_code == 403


def test_rejects_svg_disguised_as_image(client):
    result = client.post(API + "/clubs/animation/media", headers=login(client), files={"file": ("a.png", b"<svg onload='alert(1)'/>", "image/png")})
    assert result.status_code == 422


def test_member_cannot_publish_events(client):
    response = client.post(API + "/clubs/animation/events", headers=login(client), json=event_input())
    assert response.status_code == 403


def event_input(**changes):
    start = datetime.now(timezone.utc) + timedelta(days=2)
    return {"title": "一起来看片", "description": "带上半成品", "location": "活动室",
            "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=2)).isoformat(), "capacity": 1, **changes}


def test_full_event_waitlists_and_promotes_on_cancellation(client):
    member, peer, owner = login(client), login(client, "next"), login(client, "owner")
    event = client.post(API + "/clubs/animation/events", headers=owner, json=event_input()).json()
    url = API + "/events/" + event["id"] + "/registration"
    assert client.put(url, headers=member).json()["status"] == "confirmed"
    assert client.put(url, headers=member).json()["status"] == "confirmed"
    assert client.put(url, headers=peer).json()["status"] == "waiting"
    assert client.delete(url, headers=member).status_code == 204
    assert client.get(API + "/events/" + event["id"], headers=peer).json()["my_registration"] == "confirmed"
    assert client.patch(API + "/events/" + event["id"], headers=owner, json={"status": "cancelled"}).status_code == 200
    assert client.get(API + "/events/" + event["id"], headers=peer).json()["my_registration"] == "cancelled"
    assert client.put(url, headers=member).status_code == 409


def test_concurrent_registration_never_exceeds_capacity(client):
    owner = login(client, "owner")
    event = client.post(API + "/clubs/animation/events", headers=owner, json=event_input()).json()
    headers = [login(client), login(client, "next"), owner]
    def register(auth):
        response = client.put(API + "/events/" + event["id"] + "/registration", headers=auth)
        assert response.status_code == 200, response.text
        return response.json()["status"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(register, headers))
    assert statuses.count("confirmed") == 1
    assert statuses.count("waiting") == 2


@pytest.mark.parametrize("changes", [{"capacity": 0}, {"starts_at": "2026-01-01T10:00:00"}, {"ends_at": "2020-01-01T10:00:00Z"}])
def test_event_rejects_invalid_time_or_capacity(client, changes):
    response = client.post(API + "/clubs/animation/events", headers=login(client, "owner"), json=event_input(**changes))
    assert response.status_code == 422


def test_handover_requires_two_people_and_revokes_old_owner(client):
    owner, peer = login(client, "owner"), login(client, "next")
    url = API + "/clubs/animation/handovers"
    assert client.post(url, headers=owner, json={"to_user_id": "u-owner"}).status_code == 422
    item = client.post(url, headers=owner, json={"to_user_id": "u-next"}).json()
    accept = API + "/handovers/" + item["id"] + "/accept"
    assert client.post(accept, headers=owner).status_code == 403
    assert client.post(accept, headers=peer).status_code == 200
    assert client.get(API + "/clubs/animation/members", headers=owner).status_code == 403
    assert client.get(API + "/clubs/animation/members", headers=peer).status_code == 200
    assert client.post(accept, headers=peer).status_code == 200


def test_real_database_survives_restart(tmp_path):
    path = tmp_path / "persist.sqlite"
    with TestClient(create_app(path, demo=True)) as first:
        item = new_post(first)
    with TestClient(create_app(path, demo=True)) as second:
        assert second.get(API + "/posts/" + item["id"], headers=login(second)).status_code == 200


def test_revocation_applies_to_existing_session(client):
    headers = login(client)
    with sqlite3.connect(client.app.state.db_path) as db:
        db.execute("UPDATE memberships SET status='rejected' WHERE user_id='u-member'")
    assert client.get(API + "/posts/forest", headers=headers).status_code == 403
