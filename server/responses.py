"""Explicit public output contracts; provider subjects and raw storage fields stay private."""
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel
from .contracts import Kind

T = TypeVar('T')
Status = Literal['pending', 'approved', 'rejected']


class Page(BaseModel, Generic[T]):
    items: list[T]
    limit: int
    offset: int


class Health(BaseModel):
    status: Literal['ok']
    version: str
    demo: bool


class UserView(BaseModel):
    id: str
    name: str


class Session(BaseModel):
    token: str
    expires_at: float
    user: UserView


class ClubView(BaseModel):
    id: str
    name: str
    summary: str
    rules: str


class MembershipView(BaseModel):
    club_id: str
    status: Literal['pending', 'active', 'rejected']
    name: str
    role: Literal['owner', 'member']


class Profile(UserView):
    memberships: list[MembershipView]


class Member(BaseModel):
    user_id: str
    name: str
    status: Literal['pending', 'active', 'rejected']
    reason: str


class StatusView(BaseModel):
    status: str


class Post(BaseModel):
    id: str
    club_id: str
    author_id: str
    author_name: str
    kind: Kind
    title: str
    body: str
    feedback: str
    media_id: str | None
    status: Status
    reason: str
    created_at: str


class Comment(BaseModel):
    id: str
    post_id: str
    author_id: str
    author_name: str | None = None
    post_title: str | None = None
    body: str
    status: Status
    reason: str
    created_at: str


class Media(BaseModel):
    id: str
    content_type: Literal['image/png']


class Event(BaseModel):
    id: str
    club_id: str
    title: str
    description: str
    location: str
    starts_at: str
    ends_at: str
    capacity: int
    status: Literal['open', 'cancelled']
    confirmed: int
    waiting: int
    my_registration: Literal['confirmed', 'waiting', 'cancelled'] | None


class Handover(BaseModel):
    id: str
    club_id: str
    from_user_id: str
    to_user_id: str
    expires_at: str
    status: Literal['pending', 'completed', 'expired']
    club_name: str | None = None
    to_name: str | None = None
