"""
SurveyMonkey API — Pydantic models.

Organized into:
  - API response models for all resources (User, Survey, Page, Question,
    Response, Collector, Webhook, Contact, ...)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared config for API response models
# (extra="allow" prevents errors on unmapped fields)
# ---------------------------------------------------------------------------

_api = ConfigDict(extra="allow")


# ===========================================================================
# USER
# ===========================================================================


class UserMe(BaseModel):
    model_config = _api

    id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    account_type: str | None = None
    date_created: str | None = None
    date_last_login: str | None = None


# ===========================================================================
# SURVEYS
# ===========================================================================


class SurveySummary(BaseModel):
    """Single item returned by GET /surveys (list)."""
    model_config = _api

    id: str
    title: str | None = None
    href: str | None = None
    date_created: str | None = None
    date_modified: str | None = None


class SurveyList(BaseModel):
    model_config = _api

    data: list[SurveySummary] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


class SurveyDetails(BaseModel):
    """Full survey with all pages and questions."""
    model_config = _api

    id: str | None = None
    title: str | None = None
    nickname: str | None = None
    language: str | None = None
    folder_id: str | None = None
    category: str | None = None
    question_count: int | None = None
    page_count: int | None = None
    response_count: int | None = None
    date_created: str | None = None
    date_modified: str | None = None
    pages: list[dict[str, Any]] = Field(default_factory=list)


class Survey(BaseModel):
    """Single survey returned by GET /surveys/{id}."""
    model_config = _api

    id: str | None = None
    title: str | None = None
    nickname: str | None = None
    language: str | None = None
    folder_id: str | None = None
    category: str | None = None
    question_count: int | None = None
    page_count: int | None = None
    response_count: int | None = None
    date_created: str | None = None
    date_modified: str | None = None
    href: str | None = None


# ===========================================================================
# PAGES
# ===========================================================================


class Page(BaseModel):
    model_config = _api

    id: str | None = None
    title: str | None = None
    description: str | None = None
    position: int | None = None
    question_count: int | None = None
    href: str | None = None


class PageList(BaseModel):
    model_config = _api

    data: list[Page] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


# ===========================================================================
# QUESTIONS
# ===========================================================================


class QuestionAnswer(BaseModel):
    model_config = _api

    id: str | None = None
    text: str | None = None
    position: int | None = None
    visible: bool | None = None
    weight: int | None = None
    description: str | None = None
    quiz_options: dict[str, Any] | None = None
    type: str | None = None
    other: bool | None = None


class QuestionAnswers(BaseModel):
    model_config = _api

    choices: list[QuestionAnswer] = Field(default_factory=list)
    rows: list[QuestionAnswer] = Field(default_factory=list)
    cols: list[QuestionAnswer] = Field(default_factory=list)
    other: QuestionAnswer | None = None


class Question(BaseModel):
    model_config = _api

    id: str | None = None
    heading: str | None = None
    position: int | None = None
    family: str | None = None   # "single_choice", "multiple_choice", "open_ended", "matrix", etc.
    subtype: str | None = None
    required: bool | None = None
    visible: bool | None = None
    href: str | None = None
    answers: QuestionAnswers | None = None
    headings: list[dict[str, Any]] | None = None
    display_options: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None


class QuestionList(BaseModel):
    model_config = _api

    data: list[Question] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


# ===========================================================================
# RESPONSES
# ===========================================================================


class ResponseAnswer(BaseModel):
    model_config = _api

    question_id: str | None = None
    row_id: str | None = None
    col_id: str | None = None
    choice_id: str | None = None
    other_id: str | None = None
    text: str | None = None
    tag_data: list[dict[str, Any]] | None = None


class ResponsePage(BaseModel):
    model_config = _api

    id: str | None = None
    questions: list[ResponseAnswer] = Field(default_factory=list)


class SurveyResponse(BaseModel):
    model_config = _api

    id: str | None = None
    survey_id: str | None = None
    collector_id: str | None = None
    recipient_id: str | None = None
    total_time: int | None = None
    custom_value: str | None = None
    edit_url: str | None = None
    analyze_url: str | None = None
    ip_address: str | None = None
    custom_variables: dict[str, Any] | None = None
    logic_path: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    date_modified: str | None = None
    date_created: str | None = None
    href: str | None = None
    response_status: str | None = None
    collection_mode: str | None = None
    pages: list[ResponsePage] = Field(default_factory=list)


class ResponseList(BaseModel):
    model_config = _api

    data: list[SurveyResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


# ===========================================================================
# COLLECTORS
# ===========================================================================


class Collector(BaseModel):
    model_config = _api

    id: str | None = None
    name: str | None = None
    status: str | None = None   # "open" | "closed"
    type: str | None = None     # "weblink" | "email" | "sms" | "popup"
    url: str | None = None
    close_date: str | None = None
    closed_page_id: str | None = None
    redirect_type: str | None = None
    redirect_url: str | None = None
    display_survey_results: bool | None = None
    edit_response_type: str | None = None
    anonymous_type: str | None = None
    allow_multiple_responses: bool | None = None
    date_created: str | None = None
    date_modified: str | None = None
    sender_email: str | None = None
    href: str | None = None


class CollectorList(BaseModel):
    model_config = _api

    data: list[Collector] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


class CollectorMessage(BaseModel):
    model_config = _api

    id: str | None = None
    status: str | None = None   # "not_sent" | "sent"
    type: str | None = None     # "invite" | "reminder" | "thank_you" | "custom"
    href: str | None = None
    recipient_status: str | None = None
    is_scheduled: bool | None = None
    scheduled_date: str | None = None
    date_created: str | None = None
    date_modified: str | None = None
    body: str | None = None
    subject: str | None = None
    recipients_count: int | None = None


class CollectorMessageList(BaseModel):
    model_config = _api

    data: list[CollectorMessage] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


class Recipient(BaseModel):
    model_config = _api

    id: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    survey_link: str | None = None
    status: str | None = None
    removed: bool | None = None
    href: str | None = None


class RecipientList(BaseModel):
    model_config = _api

    data: list[Recipient] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


# ===========================================================================
# WEBHOOKS
# ===========================================================================


class Webhook(BaseModel):
    model_config = _api

    id: str | None = None
    name: str | None = None
    event_type: str | None = None
    object_type: str | None = None
    object_ids: list[str] | None = None
    subscription_url: str | None = None
    authorization: str | None = None
    href: str | None = None
    date_created: str | None = None
    date_modified: str | None = None

    @field_validator("object_ids", mode="before")
    @classmethod
    def _coerce_object_ids(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return [str(i) for i in v]
        return v


class WebhookList(BaseModel):
    model_config = _api

    data: list[Webhook] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


# ===========================================================================
# CONTACTS
# ===========================================================================


class Contact(BaseModel):
    model_config = _api

    id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    href: str | None = None


class ContactList(BaseModel):
    model_config = _api

    data: list[Contact] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None


class ContactGroup(BaseModel):
    """A contact list (group of contacts)."""
    model_config = _api

    id: str | None = None
    name: str | None = None
    contact_count: int | None = None
    href: str | None = None
    date_created: str | None = None
    date_modified: str | None = None


class ContactGroupList(BaseModel):
    model_config = _api

    data: list[ContactGroup] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    links: dict[str, Any] | None = None
