"""
SurveyMonkey MCP Server

Exposes the SurveyMonkey API v3 as MCP (Model Context Protocol) tools.

Direct start:
    SURVEYMONKEY_TOKEN=your_token uv run python -m surveymonkey.server

Install and run as a tool:
    uv tool install .
    SURVEYMONKEY_TOKEN=your_token surveymonkey-mcp

Install from GitHub:
    uvx --from git+https://github.com/dscovr/surveymonkey-mcp surveymonkey-mcp
"""

from __future__ import annotations

import csv
import functools
import io
import json
import logging
import os
import sys
import threading

from mcp.server.fastmcp import FastMCP

from .client import SurveyMonkeyAPIError, SurveyMonkeyClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("surveymonkey_mcp")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "surveymonkey",
    instructions=(
        "Tools for managing SurveyMonkey surveys: create, update, delete surveys, "
        "manage pages and questions, read responses, manage collectors, webhooks, and contacts."
    ),
)

# ---------------------------------------------------------------------------
# Client singleton — thread-safe (double-checked locking)
# ---------------------------------------------------------------------------

_sm_client: SurveyMonkeyClient | None = None
_client_lock = threading.Lock()


def _client() -> SurveyMonkeyClient:
    global _sm_client
    if _sm_client is None:
        with _client_lock:
            if _sm_client is None:
                _sm_client = SurveyMonkeyClient()
    return _sm_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _tool(fn):
    """
    Decorator that adds centralised error handling to every MCP tool.

    Catches SurveyMonkeyAPIError and any unexpected Exception, logs them to
    stderr, and returns a structured JSON error response instead of
    propagating the exception (which would crash the MCP process).
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SurveyMonkeyAPIError as e:
            logger.error(
                "[%s] API error %d %s: %s",
                fn.__name__, e.status_code, e.name, e.message,
            )
            return json.dumps({
                "error": True,
                "status_code": e.status_code,
                "error_id": e.error_id,
                "name": e.name,
                "message": e.message,
            }, indent=2)
        except Exception as e:
            logger.exception("[%s] Unexpected error: %s", fn.__name__, e)
            return json.dumps({
                "error": True,
                "status_code": 0,
                "error_id": "INTERNAL_ERROR",
                "name": "Internal Error",
                "message": str(e),
            }, indent=2)
    return wrapper


# ===========================================================================
# USERS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_get_me() -> str:
    """
    Returns information about the current SurveyMonkey user.
    Useful to verify the token is working and to see the username and email.
    """
    me = _client().get_me()
    return _ok(me.model_dump())


# ===========================================================================
# SURVEYS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_surveys(
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "",
    sort_order: str = "",
    title: str = "",
    start_modified_at: str = "",
    end_modified_at: str = "",
    folder_id: str = "",
) -> str:
    """
    Lists surveys in the account with pagination and optional filters.

    Args:
        page:              Page number (default 1).
        per_page:          Results per page, max 1000 (default 50).
        sort_by:           Sort field: "title", "date_modified", "num_responses" (default: date_modified).
        sort_order:        Sort direction: "asc" or "desc" (default: desc).
        title:             Filter surveys by title (substring match).
        start_modified_at: ISO 8601 — surveys modified after this date.
        end_modified_at:   ISO 8601 — surveys modified before this date.
        folder_id:         Filter by folder ID.
    """
    per_page = min(max(1, per_page), 1000)
    result = _client().list_surveys(
        page=page,
        per_page=per_page,
        sort_by=sort_by or None,
        sort_order=sort_order or None,
        title=title or None,
        start_modified_at=start_modified_at or None,
        end_modified_at=end_modified_at or None,
        folder_id=folder_id or None,
    )
    return _ok({
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "items": [
            {
                "id": s.id,
                "title": s.title,
                "date_modified": s.date_modified,
                "date_created": s.date_created,
            }
            for s in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_survey(survey_id: str) -> str:
    """
    Returns metadata for a specific survey (title, response count, dates, etc.).
    Does NOT include questions — use surveymonkey_get_survey_details for that.

    Args:
        survey_id: Survey ID.
    """
    s = _client().get_survey(survey_id)
    return _ok(s.model_dump())


@mcp.tool()
@_tool
def surveymonkey_get_survey_details(survey_id: str) -> str:
    """
    Returns the full survey definition including all pages and questions.

    Args:
        survey_id: Survey ID.
    """
    s = _client().get_survey_details(survey_id)
    return _ok(s.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_survey(survey_definition: dict) -> str:
    """
    Creates a new SurveyMonkey survey.

    Args:
        survey_definition: Survey definition as a JSON object. Structure:
            {
              "title": "My Survey",               (required)
              "nickname": "Internal name",         (optional)
              "language": "en",                    (optional, default: "en")
              "folder_id": "123",                  (optional)
              "category": "general",               (optional)
              "pages": [                           (optional — add pages at creation)
                {
                  "title": "Page 1",
                  "questions": [
                    {
                      "headings": [{"heading": "Question text"}],
                      "family": "single_choice",
                      "subtype": "vertical",
                      "answers": {
                        "choices": [
                          {"text": "Option A"},
                          {"text": "Option B"}
                        ]
                      }
                    }
                  ]
                }
              ]
            }
    """
    data = _client().create_survey(survey_definition)
    return _ok({"id": data.get("id"), "title": data.get("title"), "href": data.get("href")})


@mcp.tool()
@_tool
def surveymonkey_update_survey(survey_id: str, survey_definition: dict) -> str:
    """
    Fully replaces a survey's definition (PUT).
    Use surveymonkey_patch_survey for partial updates.

    Args:
        survey_id:         ID of the survey to update.
        survey_definition: New complete definition (same schema as surveymonkey_create_survey).
    """
    data = _client().update_survey(survey_id, survey_definition)
    return _ok({"id": data.get("id"), "title": data.get("title")})


@mcp.tool()
@_tool
def surveymonkey_patch_survey(survey_id: str, patch: dict) -> str:
    """
    Partially updates a survey (PATCH).

    Args:
        survey_id: ID of the survey.
        patch:     Object with only the fields to change.
                   Common fields: "title", "nickname", "language", "folder_id", "category".
                   Example: {"title": "New title", "language": "it"}
    """
    data = _client().patch_survey(survey_id, patch)
    return _ok({"id": data.get("id"), "title": data.get("title")})


@mcp.tool()
@_tool
def surveymonkey_delete_survey(survey_id: str) -> str:
    """
    Permanently deletes a survey and all its responses.
    WARNING: irreversible operation.

    Args:
        survey_id: ID of the survey to delete.
    """
    _client().delete_survey(survey_id)
    return _ok({
        "deleted": True,
        "survey_id": survey_id,
        "warning": "Irreversible operation: survey and all its responses permanently deleted.",
    })


# ===========================================================================
# PAGES
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_pages(
    survey_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists the pages of a survey.

    Args:
        survey_id: Survey ID.
        page:      Page number (default 1).
        per_page:  Results per page (default 50).
    """
    result = _client().list_pages(survey_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {"id": p.id, "title": p.title, "position": p.position, "question_count": p.question_count}
            for p in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_page(survey_id: str, page_id: str) -> str:
    """
    Returns the details of a specific survey page.

    Args:
        survey_id: Survey ID.
        page_id:   Page ID.
    """
    p = _client().get_page(survey_id, page_id)
    return _ok(p.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_page(survey_id: str, payload: dict) -> str:
    """
    Creates a new page in a survey.

    Args:
        survey_id: Survey ID.
        payload:   Page definition. Structure:
            {
              "title": "Page title",        (optional)
              "description": "Description", (optional)
              "position": 1                 (optional)
            }
    """
    data = _client().create_page(survey_id, payload)
    return _ok({"id": data.get("id"), "title": data.get("title"), "position": data.get("position")})


@mcp.tool()
@_tool
def surveymonkey_update_page(survey_id: str, page_id: str, payload: dict) -> str:
    """
    Updates a page in a survey (PATCH).

    Args:
        survey_id: Survey ID.
        page_id:   Page ID.
        payload:   Fields to update: "title", "description", "position".
    """
    data = _client().update_page(survey_id, page_id, payload)
    return _ok({"id": data.get("id"), "title": data.get("title")})


@mcp.tool()
@_tool
def surveymonkey_delete_page(survey_id: str, page_id: str) -> str:
    """
    Deletes a page and all its questions from a survey.
    WARNING: irreversible operation.

    Args:
        survey_id: Survey ID.
        page_id:   Page ID.
    """
    _client().delete_page(survey_id, page_id)
    return _ok({"deleted": True, "page_id": page_id})


# ===========================================================================
# QUESTIONS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_questions(
    survey_id: str,
    page_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists questions on a specific page of a survey.

    Args:
        survey_id: Survey ID.
        page_id:   Page ID.
        page:      Page number for pagination (default 1).
        per_page:  Results per page (default 50).
    """
    result = _client().list_questions(survey_id, page_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {
                "id": q.id,
                "heading": q.heading,
                "family": q.family,
                "subtype": q.subtype,
                "position": q.position,
            }
            for q in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_question(survey_id: str, page_id: str, question_id: str) -> str:
    """
    Returns the full definition of a question, including answer choices.

    Args:
        survey_id:   Survey ID.
        page_id:     Page ID.
        question_id: Question ID.
    """
    q = _client().get_question(survey_id, page_id, question_id)
    return _ok(q.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_question(survey_id: str, page_id: str, payload: dict) -> str:
    """
    Creates a new question on a survey page.

    Args:
        survey_id: Survey ID.
        page_id:   Page ID.
        payload:   Question definition. Structure:
            {
              "headings": [{"heading": "Question text"}],   (required)
              "family": "single_choice",                    (required)
              "subtype": "vertical",                        (optional)
              "position": 1,                                (optional)
              "required": false,                            (optional)
              "answers": {
                "choices": [
                  {"text": "Option A"},
                  {"text": "Option B"}
                ],
                "other": {"text": "Other (please specify)", "visible": true}
              }
            }

        Common families and subtypes:
          - single_choice:   vertical, horiz, menu
          - multiple_choice: vertical, horiz, menu
          - open_ended:      single, multi, numerical, essay
          - matrix:          rating, menu, ranking
          - rating:          star, smiley, numerical (scale 1–10)
          - demographic:     international, us
          - datetime:        both, date_only, time_only
          - presentation:    descriptive_text, image
    """
    data = _client().create_question(survey_id, page_id, payload)
    return _ok({"id": data.get("id"), "heading": data.get("heading"), "family": data.get("family")})


@mcp.tool()
@_tool
def surveymonkey_update_question(
    survey_id: str, page_id: str, question_id: str, payload: dict
) -> str:
    """
    Updates an existing question (PATCH).

    Args:
        survey_id:   Survey ID.
        page_id:     Page ID.
        question_id: Question ID.
        payload:     Fields to update (same schema as surveymonkey_create_question).
    """
    data = _client().update_question(survey_id, page_id, question_id, payload)
    return _ok({"id": data.get("id"), "heading": data.get("heading")})


@mcp.tool()
@_tool
def surveymonkey_delete_question(survey_id: str, page_id: str, question_id: str) -> str:
    """
    Deletes a question from a survey page.
    WARNING: irreversible operation.

    Args:
        survey_id:   Survey ID.
        page_id:     Page ID.
        question_id: Question ID.
    """
    _client().delete_question(survey_id, page_id, question_id)
    return _ok({"deleted": True, "question_id": question_id})


# ===========================================================================
# RESPONSES
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_responses(
    survey_id: str,
    page: int = 1,
    per_page: int = 50,
    start_created_at: str = "",
    end_created_at: str = "",
    status: str = "",
    email: str = "",
    sort_by: str = "",
    sort_order: str = "",
) -> str:
    """
    Lists responses for a survey (metadata only, no answers).
    Use surveymonkey_list_responses_bulk to include answer data.

    Args:
        survey_id:        Survey ID.
        page:             Page number (default 1).
        per_page:         Results per page, max 1000 (default 50).
        start_created_at: ISO 8601 — responses created after this date.
        end_created_at:   ISO 8601 — responses created before this date.
        status:           Filter by status: "completed", "partial", "overquota", "disqualified".
        email:            Filter by respondent email.
        sort_by:          Sort field: "date_modified".
        sort_order:       Sort direction: "asc" or "desc".
    """
    per_page = min(max(1, per_page), 1000)
    result = _client().list_responses(
        survey_id,
        page=page,
        per_page=per_page,
        start_created_at=start_created_at or None,
        end_created_at=end_created_at or None,
        status=status or None,
        email=email or None,
        sort_by=sort_by or None,
        sort_order=sort_order or None,
    )
    return _ok({
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "items": [
            {
                "id": r.id,
                "response_status": r.response_status,
                "date_created": r.date_created,
                "date_modified": r.date_modified,
                "collector_id": r.collector_id,
                "ip_address": r.ip_address,
                "total_time": r.total_time,
            }
            for r in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_list_responses_bulk(
    survey_id: str,
    page: int = 1,
    per_page: int = 50,
    simple: bool = False,
    start_created_at: str = "",
    end_created_at: str = "",
    status: str = "",
    collector_ids: str = "",
    page_ids: str = "",
    question_ids: str = "",
) -> str:
    """
    Lists responses for a survey including all answer data.

    Args:
        survey_id:        Survey ID.
        page:             Page number (default 1).
        per_page:         Results per page, max 1000 (default 50).
        simple:           If true, returns simplified answer format (default false).
        start_created_at: ISO 8601 — responses created after this date.
        end_created_at:   ISO 8601 — responses created before this date.
        status:           Filter: "completed", "partial", "overquota", "disqualified".
        collector_ids:    Comma-separated collector IDs to filter by.
        page_ids:         Comma-separated page IDs to include.
        question_ids:     Comma-separated question IDs to include.
    """
    per_page = min(max(1, per_page), 1000)
    result = _client().list_responses_bulk(
        survey_id,
        page=page,
        per_page=per_page,
        simple=simple,
        start_created_at=start_created_at or None,
        end_created_at=end_created_at or None,
        status=status or None,
        collector_ids=[c.strip() for c in collector_ids.split(",") if c.strip()] if collector_ids else None,
        page_ids=[p.strip() for p in page_ids.split(",") if p.strip()] if page_ids else None,
        question_ids=[q.strip() for q in question_ids.split(",") if q.strip()] if question_ids else None,
    )
    return _ok({
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "items": [r.model_dump() for r in result.data],
    })


@mcp.tool()
@_tool
def surveymonkey_get_response(survey_id: str, response_id: str) -> str:
    """
    Returns metadata for a specific response (no answers).
    Use surveymonkey_get_response_details for answers.

    Args:
        survey_id:   Survey ID.
        response_id: Response ID.
    """
    r = _client().get_response(survey_id, response_id)
    return _ok(r.model_dump())


@mcp.tool()
@_tool
def surveymonkey_get_response_details(
    survey_id: str,
    response_id: str,
    page_ids: str = "",
    question_ids: str = "",
    simple: bool = False,
) -> str:
    """
    Returns a specific response with all answer data.

    Args:
        survey_id:    Survey ID.
        response_id:  Response ID.
        page_ids:     Comma-separated page IDs to include (empty = all pages).
        question_ids: Comma-separated question IDs to include (empty = all questions).
        simple:       If true, returns simplified answer format (default false).
    """
    data = _client().get_response_details(
        survey_id,
        response_id,
        page_ids=[p.strip() for p in page_ids.split(",") if p.strip()] if page_ids else None,
        question_ids=[q.strip() for q in question_ids.split(",") if q.strip()] if question_ids else None,
        simple=simple,
    )
    return _ok(data)


@mcp.tool()
@_tool
def surveymonkey_delete_response(survey_id: str, response_id: str) -> str:
    """
    Permanently deletes a specific response.
    WARNING: irreversible operation.

    Args:
        survey_id:   Survey ID.
        response_id: Response ID to delete.
    """
    _client().delete_response(survey_id, response_id)
    return _ok({
        "deleted": True,
        "response_id": response_id,
        "warning": "Irreversible operation: response permanently deleted.",
    })


@mcp.tool()
@_tool
def surveymonkey_export_responses_csv(
    survey_id: str,
    start_created_at: str = "",
    end_created_at: str = "",
    status: str = "",
) -> str:
    """
    Exports all responses for a survey as CSV (includes all answers).
    Handles pagination automatically, collecting up to 10,000 responses.

    Args:
        survey_id:        Survey ID.
        start_created_at: ISO 8601 — export responses created after this date.
        end_created_at:   ISO 8601 — export responses created before this date.
        status:           Filter by status: "completed", "partial", etc. (empty = all).

    Returns:
        CSV text with headers in the first row.
    """
    all_responses = []
    page = 1
    max_responses = 10_000

    while len(all_responses) < max_responses:
        result = _client().list_responses_bulk(
            survey_id,
            page=page,
            per_page=100,
            simple=True,
            start_created_at=start_created_at or None,
            end_created_at=end_created_at or None,
            status=status or None,
        )
        all_responses.extend(result.data)
        if len(result.data) < 100:
            break
        page += 1

    base_columns = ["response_id", "date_created", "date_modified", "response_status", "collector_id", "ip_address", "total_time"]

    if not all_responses:
        return ",".join(base_columns) + "\n"

    # Flatten answers: collect all unique (question_id, row_id, col_id) tuples
    # to handle matrix and multi-row questions correctly.
    answer_keys: list[tuple[str, str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for r in all_responses:
        for pg in r.pages:
            for ans in pg.questions:
                if ans.question_id:
                    key = (ans.question_id, ans.row_id or "", ans.col_id or "")
                    if key not in seen_keys:
                        answer_keys.append(key)
                        seen_keys.add(key)

    # Build readable column names: "qid", "qid[row]", "qid[row][col]"
    def _col_name(qid: str, row: str, col: str) -> str:
        name = qid
        if row:
            name += f"[{row}]"
        if col:
            name += f"[{col}]"
        return name

    answer_col_names = [_col_name(*k) for k in answer_keys]
    header = base_columns + answer_col_names

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)

    for r in all_responses:
        # Build a mapping (question_id, row_id, col_id) -> text
        answers_map: dict[tuple[str, str, str], str] = {}
        for pg in r.pages:
            for ans in pg.questions:
                if ans.question_id:
                    key = (ans.question_id, ans.row_id or "", ans.col_id or "")
                    value = ans.text or ""
                    if key in answers_map and answers_map[key]:
                        answers_map[key] += f"; {value}"
                    else:
                        answers_map[key] = value

        row = [
            r.id or "",
            r.date_created or "",
            r.date_modified or "",
            r.response_status or "",
            r.collector_id or "",
            r.ip_address or "",
            str(r.total_time) if r.total_time is not None else "",
        ] + [answers_map.get(k, "") for k in answer_keys]
        writer.writerow(row)

    return buf.getvalue()


# ===========================================================================
# COLLECTORS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_collectors(
    survey_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists all collectors for a survey.

    Args:
        survey_id: Survey ID.
        page:      Page number (default 1).
        per_page:  Results per page (default 50).
    """
    result = _client().list_collectors(survey_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "status": c.status,
                "url": c.url,
                "date_created": c.date_created,
            }
            for c in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_collector(collector_id: str) -> str:
    """
    Returns the details of a specific collector.

    Args:
        collector_id: Collector ID.
    """
    c = _client().get_collector(collector_id)
    return _ok(c.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_collector(survey_id: str, payload: dict) -> str:
    """
    Creates a new collector for a survey.

    Args:
        survey_id: Survey ID.
        payload:   Collector definition. Structure:
            {
              "type": "weblink",            (required: "weblink", "email", "sms", "popup")
              "name": "Collector name",     (optional)
              "status": "open",             (optional: "open" | "closed")
              "thank_you_message": "...",   (optional)
              "close_date": "2026-12-31",   (optional — ISO 8601 date)
              "redirect_url": "https://...", (optional — redirect after completion)
              "allow_multiple_responses": false (optional)
            }
    """
    data = _client().create_collector(survey_id, payload)
    return _ok({"id": data.get("id"), "name": data.get("name"), "type": data.get("type"), "url": data.get("url")})


@mcp.tool()
@_tool
def surveymonkey_update_collector(collector_id: str, payload: dict) -> str:
    """
    Updates a collector (PATCH).

    Args:
        collector_id: Collector ID.
        payload:      Fields to update. Common fields:
                      "name", "status" ("open"|"closed"), "close_date",
                      "redirect_url", "allow_multiple_responses".
    """
    data = _client().update_collector(collector_id, payload)
    return _ok({"id": data.get("id"), "name": data.get("name"), "status": data.get("status")})


@mcp.tool()
@_tool
def surveymonkey_delete_collector(collector_id: str) -> str:
    """
    Deletes a collector and all its responses.
    WARNING: irreversible operation.

    Args:
        collector_id: Collector ID.
    """
    _client().delete_collector(collector_id)
    return _ok({
        "deleted": True,
        "collector_id": collector_id,
        "warning": "Irreversible operation: collector and its responses permanently deleted.",
    })


# ===========================================================================
# COLLECTOR MESSAGES
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_collector_messages(
    collector_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists email messages for a collector.

    Args:
        collector_id: Collector ID (must be of type "email").
        page:         Page number (default 1).
        per_page:     Results per page (default 50).
    """
    result = _client().list_collector_messages(collector_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {
                "id": m.id,
                "type": m.type,
                "status": m.status,
                "subject": m.subject,
                "is_scheduled": m.is_scheduled,
                "scheduled_date": m.scheduled_date,
                "recipients_count": m.recipients_count,
            }
            for m in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_create_collector_message(collector_id: str, payload: dict) -> str:
    """
    Creates a new email message for a collector.

    Args:
        collector_id: Collector ID (must be of type "email").
        payload:      Message definition. Structure:
            {
              "type": "invite",                 (required: "invite" | "reminder" | "thank_you" | "custom")
              "subject": "Please take our survey", (optional)
              "body_text": "Click here: [SurveyLink]",  (optional)
              "from_name": "Sender Name",        (optional)
              "reply_to": "reply@example.com"    (optional)
            }
    """
    m = _client().create_collector_message(collector_id, payload)
    return _ok(m.model_dump())


@mcp.tool()
@_tool
def surveymonkey_send_collector_message(
    collector_id: str,
    message_id: str,
    scheduled_date: str = "",
) -> str:
    """
    Sends an email message to all recipients of a collector.

    Args:
        collector_id:   Collector ID.
        message_id:     Message ID to send.
        scheduled_date: ISO 8601 datetime to schedule the send (empty = send immediately).
    """
    data = _client().send_collector_message(
        collector_id, message_id, scheduled_date=scheduled_date or None
    )
    return _ok(data)


@mcp.tool()
@_tool
def surveymonkey_list_collector_recipients(
    collector_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists email recipients for a collector.

    Args:
        collector_id: Collector ID.
        page:         Page number (default 1).
        per_page:     Results per page (default 50).
    """
    result = _client().list_collector_recipients(collector_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {
                "id": r.id,
                "email": r.email,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "status": r.status,
            }
            for r in result.data
        ],
    })


# ===========================================================================
# WEBHOOKS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_webhooks(page: int = 1, per_page: int = 50) -> str:
    """
    Lists all webhooks in the account.

    Args:
        page:     Page number (default 1).
        per_page: Results per page (default 50).
    """
    result = _client().list_webhooks(page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {
                "id": w.id,
                "name": w.name,
                "event_type": w.event_type,
                "object_type": w.object_type,
                "subscription_url": w.subscription_url,
            }
            for w in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_webhook(webhook_id: str) -> str:
    """
    Returns the details of a specific webhook.

    Args:
        webhook_id: Webhook ID.
    """
    w = _client().get_webhook(webhook_id)
    return _ok(w.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_webhook(payload: dict) -> str:
    """
    Creates a new webhook.

    Args:
        payload: Webhook definition. Structure:
            {
              "name": "My Webhook",                         (required)
              "event_type": "response_completed",           (required)
              "object_type": "survey",                      (required: "survey" | "collector")
              "object_ids": ["12345678"],                   (required — list of survey/collector IDs)
              "subscription_url": "https://...",            (required — HTTPS endpoint)
              "authorization": "Bearer token_for_your_url" (optional — sent in callback header)
            }

        Supported event_types:
          response_completed, response_disqualified, response_updated,
          response_created, response_deleted, response_overquota,
          survey_created, survey_updated, survey_deleted,
          collector_created, collector_updated, collector_deleted
    """
    w = _client().create_webhook(payload)
    return _ok(w.model_dump())


@mcp.tool()
@_tool
def surveymonkey_update_webhook(webhook_id: str, payload: dict) -> str:
    """
    Updates a webhook (PATCH).

    Args:
        webhook_id: Webhook ID.
        payload:    Fields to update (same schema as surveymonkey_create_webhook).
    """
    w = _client().update_webhook(webhook_id, payload)
    return _ok(w.model_dump())


@mcp.tool()
@_tool
def surveymonkey_delete_webhook(webhook_id: str) -> str:
    """
    Deletes a webhook.

    Args:
        webhook_id: Webhook ID.
    """
    _client().delete_webhook(webhook_id)
    return _ok({"deleted": True, "webhook_id": webhook_id})


# ===========================================================================
# CONTACTS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_contacts(
    page: int = 1,
    per_page: int = 50,
    status: str = "",
    search_by: str = "",
    search: str = "",
    sort_by: str = "",
    sort_order: str = "",
) -> str:
    """
    Lists contacts in the account.

    Args:
        page:       Page number (default 1).
        per_page:   Results per page (default 50).
        status:     Filter by status: "active", "optedout", "bounced".
        search_by:  Field to search by: "email", "first_name", "last_name".
        search:     Search term.
        sort_by:    Sort field: "email", "first_name", "last_name".
        sort_order: Sort direction: "asc" or "desc".
    """
    result = _client().list_contacts(
        page=page,
        per_page=per_page,
        status=status or None,
        search_by=search_by or None,
        search=search or None,
        sort_by=sort_by or None,
        sort_order=sort_order or None,
    )
    return _ok({
        "total": result.total,
        "items": [
            {"id": c.id, "email": c.email, "first_name": c.first_name, "last_name": c.last_name}
            for c in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_contact(contact_id: str) -> str:
    """
    Returns the details of a specific contact.

    Args:
        contact_id: Contact ID.
    """
    c = _client().get_contact(contact_id)
    return _ok(c.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_contact(
    email: str,
    first_name: str = "",
    last_name: str = "",
) -> str:
    """
    Creates a new contact.

    Args:
        email:      Contact email address (required).
        first_name: First name (optional).
        last_name:  Last name (optional).
    """
    payload: dict = {"email": email}
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    c = _client().create_contact(payload)
    return _ok(c.model_dump())


@mcp.tool()
@_tool
def surveymonkey_update_contact(contact_id: str, payload: dict) -> str:
    """
    Updates an existing contact (PATCH).

    Args:
        contact_id: Contact ID.
        payload:    Fields to update. Common fields:
                    "email", "first_name", "last_name".
                    Example: {"first_name": "Jane", "last_name": "Doe"}
    """
    c = _client().update_contact(contact_id, payload)
    return _ok(c.model_dump())


@mcp.tool()
@_tool
def surveymonkey_delete_contact(contact_id: str) -> str:
    """
    Deletes a contact.

    Args:
        contact_id: Contact ID.
    """
    _client().delete_contact(contact_id)
    return _ok({"deleted": True, "contact_id": contact_id})


# ===========================================================================
# CONTACT LISTS
# ===========================================================================


@mcp.tool()
@_tool
def surveymonkey_list_contact_lists(page: int = 1, per_page: int = 50) -> str:
    """
    Lists all contact lists in the account.

    Args:
        page:     Page number (default 1).
        per_page: Results per page (default 50).
    """
    result = _client().list_contact_lists(page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {"id": g.id, "name": g.name, "contact_count": g.contact_count}
            for g in result.data
        ],
    })


@mcp.tool()
@_tool
def surveymonkey_get_contact_list(list_id: str) -> str:
    """
    Returns the details of a specific contact list.

    Args:
        list_id: Contact list ID.
    """
    g = _client().get_contact_list(list_id)
    return _ok(g.model_dump())


@mcp.tool()
@_tool
def surveymonkey_create_contact_list(name: str) -> str:
    """
    Creates a new contact list.

    Args:
        name: Name for the new contact list.
    """
    g = _client().create_contact_list(name)
    return _ok(g.model_dump())


@mcp.tool()
@_tool
def surveymonkey_delete_contact_list(list_id: str) -> str:
    """
    Deletes a contact list.

    Args:
        list_id: Contact list ID.
    """
    _client().delete_contact_list(list_id)
    return _ok({"deleted": True, "list_id": list_id})


@mcp.tool()
@_tool
def surveymonkey_list_contact_list_members(
    list_id: str,
    page: int = 1,
    per_page: int = 50,
) -> str:
    """
    Lists contacts that belong to a specific contact list.

    Args:
        list_id:  Contact list ID.
        page:     Page number (default 1).
        per_page: Results per page (default 50).
    """
    result = _client().list_contact_list_members(list_id, page=page, per_page=per_page)
    return _ok({
        "total": result.total,
        "items": [
            {"id": c.id, "email": c.email, "first_name": c.first_name, "last_name": c.last_name}
            for c in result.data
        ],
    })


# ===========================================================================
# Entrypoint
# ===========================================================================


def main() -> None:
    token = os.environ.get("SURVEYMONKEY_TOKEN")
    if not token:
        print(
            "Error: SURVEYMONKEY_TOKEN environment variable is not set.\n"
            "Usage: SURVEYMONKEY_TOKEN=your_token surveymonkey-mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    logger.info("Starting SurveyMonkey MCP server (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
