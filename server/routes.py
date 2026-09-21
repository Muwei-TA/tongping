"""HTTP translation only. Authorization and product rules live in services."""
from typing import Annotated, Literal
from fastapi import APIRouter, Query, Request, Response, UploadFile
from . import clubs, identity, content, media, events, governance
from .contracts import (DemoLogin, CodeLogin, Join, MembershipReview, PostInput,
                        CommentInput, Review, Kind, EventInput, CancelEvent, HandoverInput)
from . import responses as out
from .dependencies import Database, User, Authorization

router = APIRouter(prefix="/api/v1")
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=100000)]


@router.get("/health", response_model=out.Health)
def health(request: Request):
    return {"status": "ok", "version": "0.1.0", "demo": request.app.state.demo}


@router.post("/auth/demo", response_model=out.Session)
def demo_login(data: DemoLogin, db: Database, request: Request):
    return identity.demo_login(db, data.persona, request.app.state.demo)


@router.post("/auth/code", response_model=out.Session)
def code_login(data: CodeLogin, db: Database):
    return identity.code_login(db, data.provider, data.code)


@router.delete("/auth/session", status_code=204)
def logout(db: Database, user: User, authorization: Authorization = None):
    identity.logout(db, authorization)
    return Response(status_code=204)


@router.get("/me", response_model=out.Profile)
def profile(db: Database, user: User):
    return clubs.profile(db, user)


@router.get("/clubs", response_model=out.Page[out.ClubView])
def list_clubs(db: Database, limit: Limit = 20, offset: Offset = 0):
    return clubs.list_clubs(db, limit, offset)


@router.get("/clubs/{club_id}", response_model=out.ClubView)
def club(club_id: str, db: Database):
    return clubs.get_club(db, club_id)


@router.post("/clubs/{club_id}/membership", response_model=out.StatusView)
def apply(club_id: str, data: Join, db: Database, user: User):
    return clubs.apply(db, club_id, user["id"], data.reason)


@router.get("/clubs/{club_id}/members", response_model=out.Page[out.Member])
def members(club_id: str, db: Database, user: User, limit: Limit = 20, offset: Offset = 0):
    return clubs.members(db, club_id, user["id"], limit, offset)


@router.patch("/clubs/{club_id}/members/{user_id}", response_model=out.StatusView)
def review_member(club_id: str, user_id: str, data: MembershipReview, db: Database, user: User):
    return clubs.review_member(db, club_id, user["id"], user_id, data.status)


@router.get("/clubs/{club_id}/posts", response_model=out.Page[out.Post])
def posts(club_id: str, db: Database, user: User, kind: Kind | None = None,
          q: Annotated[str, Query(max_length=100)] = "", mine: bool = False,
          status: Literal["pending", "approved", "rejected"] | None = None,
          limit: Limit = 20, offset: Offset = 0):
    return content.list_posts(db, club_id, user["id"], kind, q, mine, status, limit, offset)


@router.post("/clubs/{club_id}/posts", status_code=201, response_model=out.Post)
def publish(club_id: str, data: PostInput, db: Database, user: User):
    return content.create_post(db, club_id, user["id"], data)


@router.get("/posts/{post_id}", response_model=out.Post)
def post(post_id: str, db: Database, user: User):
    return content.get_post(db, post_id, user["id"])


@router.patch("/posts/{post_id}/review", response_model=out.Post)
def review_post(post_id: str, data: Review, db: Database, user: User):
    return content.review_post(db, post_id, user["id"], data)


@router.get("/posts/{post_id}/comments", response_model=out.Page[out.Comment])
def comments(post_id: str, db: Database, user: User, limit: Limit = 20, offset: Offset = 0):
    return content.list_comments(db, post_id, user["id"], limit, offset)


@router.post("/posts/{post_id}/comments", status_code=201, response_model=out.Comment)
def comment(post_id: str, data: CommentInput, db: Database, user: User):
    return content.create_comment(db, post_id, user["id"], data.body)


@router.patch("/comments/{comment_id}/review", response_model=out.Comment)
def review_comment(comment_id: str, data: Review, db: Database, user: User):
    return content.review_comment(db, comment_id, user["id"], data)


@router.get("/clubs/{club_id}/review-comments", response_model=out.Page[out.Comment])
def review_comments(club_id: str, db: Database, user: User, limit: Limit = 20, offset: Offset = 0):
    return content.pending_comments(db, club_id, user["id"], limit, offset)


@router.post("/clubs/{club_id}/media", status_code=201, response_model=out.Media)
def upload(club_id: str, file: UploadFile, db: Database, user: User):
    raw = file.file.read(media.MAX_UPLOAD + 1)
    return media.upload(db, club_id, user["id"], raw)


@router.get("/media/{media_id}")
def download(media_id: str, db: Database, user: User):
    data, mime = media.download(db, media_id, user["id"])
    return Response(data, media_type=mime)


@router.get("/clubs/{club_id}/events", response_model=out.Page[out.Event])
def event_list(club_id: str, db: Database, user: User, limit: Limit = 20, offset: Offset = 0):
    return events.list_events(db, club_id, user["id"], limit, offset)


@router.post("/clubs/{club_id}/events", status_code=201, response_model=out.Event)
def event_create(club_id: str, data: EventInput, db: Database, user: User):
    return events.create_event(db, club_id, user["id"], data)


@router.get("/events/{event_id}", response_model=out.Event)
def event_detail(event_id: str, db: Database, user: User):
    return events.get_event(db, event_id, user["id"])


@router.put("/events/{event_id}/registration", response_model=out.StatusView)
def register(event_id: str, db: Database, user: User):
    return events.register(db, event_id, user["id"])


@router.delete("/events/{event_id}/registration", status_code=204)
def unregister(event_id: str, db: Database, user: User):
    events.cancel_registration(db, event_id, user["id"])
    return Response(status_code=204)


@router.patch("/events/{event_id}", response_model=out.Event)
def cancel_event(event_id: str, data: CancelEvent, db: Database, user: User):
    return events.cancel_event(db, event_id, user["id"])


@router.get("/me/handovers", response_model=out.Page[out.Handover])
def handovers(db: Database, user: User, limit: Limit = 20, offset: Offset = 0):
    return governance.handovers(db, user["id"], limit, offset)


@router.post("/clubs/{club_id}/handovers", status_code=201, response_model=out.Handover)
def start_handover(club_id: str, data: HandoverInput, db: Database, user: User):
    return governance.start_handover(db, club_id, user["id"], data.to_user_id)


@router.post("/handovers/{handover_id}/accept", response_model=out.Handover)
def accept_handover(handover_id: str, db: Database, user: User):
    return governance.accept_handover(db, handover_id, user["id"])
