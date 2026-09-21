"""Validated input contracts. Unrecognized fields never grant privileges."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["work", "knowledge", "question", "chat"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DemoLogin(Input):
    persona: Literal["member", "owner", "next", "applicant", "outsider"]


class CodeLogin(Input):
    provider: Literal["wechat", "qq"]
    code: str = Field(min_length=1, max_length=256)


class Join(Input):
    reason: str = Field(min_length=2, max_length=500)
    accept_rules: Literal[True]


class MembershipReview(Input):
    status: Literal["active", "rejected"]


class PostInput(Input):
    client_id: str = Field(min_length=1, max_length=80)
    kind: Kind
    title: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=10000)
    feedback: str = Field(default="", max_length=500)
    media_id: str | None = Field(default=None, max_length=80)


class CommentInput(Input):
    body: str = Field(min_length=2, max_length=2000)


class Review(Input):
    status: Literal["approved", "rejected"]
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def rejection_needs_reason(self):
        if self.status == "rejected" and not self.reason:
            raise ValueError("请填写退回理由")
        return self


class EventInput(Input):
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=2, max_length=5000)
    location: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=1, le=1000, strict=True)

    @model_validator(mode="after")
    def valid_times(self):
        if not self.starts_at.tzinfo or not self.ends_at.tzinfo:
            raise ValueError("日期必须包含时区")
        if self.starts_at <= datetime.now(timezone.utc) or self.ends_at <= self.starts_at:
            raise ValueError("活动须在未来开始，结束须晚于开始")
        self.starts_at = self.starts_at.astimezone(timezone.utc)
        self.ends_at = self.ends_at.astimezone(timezone.utc)
        return self


class CancelEvent(Input):
    status: Literal["cancelled"]


class HandoverInput(Input):
    to_user_id: str = Field(min_length=1, max_length=80)
