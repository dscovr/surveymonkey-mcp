"""
SurveyMonkey API — full-featured HTTP client.

Covers all public endpoints:
  - Users         GET /users/me
  - Surveys       CRUD + details
  - Pages         CRUD
  - Questions     CRUD
  - Responses     list, bulk, get details, delete
  - Collectors    CRUD + messages + recipients
  - Webhooks      CRUD
  - Contacts      CRUD
  - Contact Lists CRUD + members
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from .models import (
    Collector,
    CollectorList,
    CollectorMessage,
    CollectorMessageList,
    Contact,
    ContactGroup,
    ContactGroupList,
    ContactList,
    Page,
    PageList,
    Question,
    QuestionList,
    Recipient,
    RecipientList,
    ResponseList,
    Survey,
    SurveyDetails,
    SurveyList,
    SurveyResponse,
    UserMe,
    Webhook,
    WebhookList,
)

logger = logging.getLogger(__name__)

SURVEYMONKEY_API_URL = "https://api.surveymonkey.com/v3"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class SurveyMonkeyAPIError(Exception):
    """Raised for non-2xx HTTP responses from the SurveyMonkey API."""

    def __init__(
        self,
        status_code: int,
        error_id: str,
        name: str,
        message: str,
    ) -> None:
        self.status_code = status_code
        self.error_id = error_id
        self.name = name
        self.message = message
        super().__init__(f"[{status_code}] {name} ({error_id}): {message}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SurveyMonkeyClient:
    """
    Full-featured client for the SurveyMonkey API v3.

    Usage:
        client = SurveyMonkeyClient(token="your_access_token")
        # or using the SURVEYMONKEY_TOKEN environment variable
        client = SurveyMonkeyClient()
    """

    def __init__(self, token: str | None = None, timeout: int = 30) -> None:
        self.token = token or os.environ["SURVEYMONKEY_TOKEN"]
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _headers(self, content_type: str | None = "application/json") -> dict:
        h: dict[str, str] = {"Authorization": f"bearer {self.token}"}
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        content_type: str | None = "application/json",
        _retries: int = 3,
    ) -> requests.Response:
        """Executes the HTTP request with retry on 429/503 and raises SurveyMonkeyAPIError on error."""
        url = f"{SURVEYMONKEY_API_URL}{path}"
        for attempt in range(_retries + 1):
            resp = self._session.request(
                method,
                url,
                headers=self._headers(content_type),
                params=_clean_params(params),
                json=json,
                timeout=self.timeout,
            )
            if resp.status_code in (429, 503) and attempt < _retries:
                wait = min(2 ** attempt, 30)
                retry_after = resp.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    wait = int(retry_after)
                logger.warning(
                    "%s %s → %d, retry %d/%d in %ds",
                    method, path, resp.status_code, attempt + 1, _retries, wait,
                )
                time.sleep(wait)
                continue
            if not resp.ok:
                try:
                    body = resp.json()
                    err = body.get("error", {})
                except Exception:
                    err = {}
                raise SurveyMonkeyAPIError(
                    status_code=resp.status_code,
                    error_id=str(err.get("id", "UNKNOWN")),
                    name=err.get("name", "Unknown Error"),
                    message=err.get("message", resp.text),
                )
            return resp
        raise SurveyMonkeyAPIError(
            status_code=0,
            error_id="MAX_RETRIES",
            name="Max Retries Exceeded",
            message="The request failed after the maximum number of retries.",
        )

    # ==================================================================
    # USERS
    # ==================================================================

    def get_me(self) -> UserMe:
        """GET /users/me — current user information."""
        resp = self._request("GET", "/users/me")
        return UserMe.model_validate(resp.json())

    # ==================================================================
    # SURVEYS
    # ==================================================================

    def list_surveys(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        sort_by: str | None = None,
        sort_order: str | None = None,
        title: str | None = None,
        start_modified_at: str | None = None,
        end_modified_at: str | None = None,
        folder_id: str | None = None,
    ) -> SurveyList:
        """GET /surveys — list surveys with pagination and optional filters."""
        resp = self._request(
            "GET",
            "/surveys",
            params={
                "page": page,
                "per_page": per_page,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "title": title,
                "start_modified_at": start_modified_at,
                "end_modified_at": end_modified_at,
                "folder_id": folder_id,
            },
        )
        return SurveyList.model_validate(resp.json())

    def get_survey(self, survey_id: str) -> Survey:
        """GET /surveys/{survey_id} — retrieve a survey."""
        resp = self._request("GET", f"/surveys/{survey_id}")
        return Survey.model_validate(resp.json())

    def get_survey_details(self, survey_id: str) -> SurveyDetails:
        """GET /surveys/{survey_id}/details — full survey with all pages and questions."""
        resp = self._request("GET", f"/surveys/{survey_id}/details")
        return SurveyDetails.model_validate(resp.json())

    def create_survey(self, payload: dict) -> dict:
        """POST /surveys — create a new survey."""
        resp = self._request("POST", "/surveys", json=payload)
        return resp.json()

    def update_survey(self, survey_id: str, payload: dict) -> dict:
        """PUT /surveys/{survey_id} — replace a survey."""
        resp = self._request("PUT", f"/surveys/{survey_id}", json=payload)
        return resp.json()

    def patch_survey(self, survey_id: str, payload: dict) -> dict:
        """PATCH /surveys/{survey_id} — partially update a survey."""
        resp = self._request("PATCH", f"/surveys/{survey_id}", json=payload)
        return resp.json()

    def delete_survey(self, survey_id: str) -> None:
        """DELETE /surveys/{survey_id} — delete a survey."""
        self._request("DELETE", f"/surveys/{survey_id}")

    # ==================================================================
    # PAGES
    # ==================================================================

    def list_pages(
        self,
        survey_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> PageList:
        """GET /surveys/{survey_id}/pages — list pages for a survey."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/pages",
            params={"page": page, "per_page": per_page},
        )
        return PageList.model_validate(resp.json())

    def get_page(self, survey_id: str, page_id: str) -> Page:
        """GET /surveys/{survey_id}/pages/{page_id} — retrieve a page."""
        resp = self._request("GET", f"/surveys/{survey_id}/pages/{page_id}")
        return Page.model_validate(resp.json())

    def create_page(self, survey_id: str, payload: dict) -> dict:
        """POST /surveys/{survey_id}/pages — create a new page."""
        resp = self._request("POST", f"/surveys/{survey_id}/pages", json=payload)
        return resp.json()

    def update_page(self, survey_id: str, page_id: str, payload: dict) -> dict:
        """PATCH /surveys/{survey_id}/pages/{page_id} — update a page."""
        resp = self._request(
            "PATCH", f"/surveys/{survey_id}/pages/{page_id}", json=payload
        )
        return resp.json()

    def delete_page(self, survey_id: str, page_id: str) -> None:
        """DELETE /surveys/{survey_id}/pages/{page_id} — delete a page."""
        self._request("DELETE", f"/surveys/{survey_id}/pages/{page_id}")

    # ==================================================================
    # QUESTIONS
    # ==================================================================

    def list_questions(
        self,
        survey_id: str,
        page_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> QuestionList:
        """GET /surveys/{survey_id}/pages/{page_id}/questions — list questions."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/pages/{page_id}/questions",
            params={"page": page, "per_page": per_page},
        )
        return QuestionList.model_validate(resp.json())

    def get_question(
        self, survey_id: str, page_id: str, question_id: str
    ) -> Question:
        """GET /surveys/{survey_id}/pages/{page_id}/questions/{question_id} — retrieve a question."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/pages/{page_id}/questions/{question_id}",
        )
        return Question.model_validate(resp.json())

    def create_question(
        self, survey_id: str, page_id: str, payload: dict
    ) -> dict:
        """POST /surveys/{survey_id}/pages/{page_id}/questions — create a question."""
        resp = self._request(
            "POST",
            f"/surveys/{survey_id}/pages/{page_id}/questions",
            json=payload,
        )
        return resp.json()

    def update_question(
        self, survey_id: str, page_id: str, question_id: str, payload: dict
    ) -> dict:
        """PATCH /surveys/{survey_id}/pages/{page_id}/questions/{question_id} — update a question."""
        resp = self._request(
            "PATCH",
            f"/surveys/{survey_id}/pages/{page_id}/questions/{question_id}",
            json=payload,
        )
        return resp.json()

    def delete_question(
        self, survey_id: str, page_id: str, question_id: str
    ) -> None:
        """DELETE /surveys/{survey_id}/pages/{page_id}/questions/{question_id} — delete a question."""
        self._request(
            "DELETE",
            f"/surveys/{survey_id}/pages/{page_id}/questions/{question_id}",
        )

    # ==================================================================
    # RESPONSES
    # ==================================================================

    def list_responses(
        self,
        survey_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
        start_created_at: str | None = None,
        end_created_at: str | None = None,
        status: str | None = None,
        email: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> ResponseList:
        """GET /surveys/{survey_id}/responses — list responses with filters."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/responses",
            params={
                "page": page,
                "per_page": per_page,
                "start_created_at": start_created_at,
                "end_created_at": end_created_at,
                "status": status,
                "email": email,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        return ResponseList.model_validate(resp.json())

    def list_responses_bulk(
        self,
        survey_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
        simple: bool = False,
        start_created_at: str | None = None,
        end_created_at: str | None = None,
        status: str | None = None,
        collector_ids: list[str] | None = None,
        page_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
    ) -> ResponseList:
        """GET /surveys/{survey_id}/responses/bulk — bulk responses with answers."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/responses/bulk",
            params={
                "page": page,
                "per_page": per_page,
                "simple": "true" if simple else None,
                "start_created_at": start_created_at,
                "end_created_at": end_created_at,
                "status": status,
                "collector_ids": ",".join(collector_ids) if collector_ids else None,
                "page_ids": ",".join(page_ids) if page_ids else None,
                "question_ids": ",".join(question_ids) if question_ids else None,
            },
        )
        return ResponseList.model_validate(resp.json())

    def get_response(self, survey_id: str, response_id: str) -> SurveyResponse:
        """GET /surveys/{survey_id}/responses/{response_id} — retrieve a response."""
        resp = self._request(
            "GET", f"/surveys/{survey_id}/responses/{response_id}"
        )
        return SurveyResponse.model_validate(resp.json())

    def get_response_details(
        self,
        survey_id: str,
        response_id: str,
        *,
        page_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        simple: bool = False,
    ) -> dict:
        """GET /surveys/{survey_id}/responses/{response_id}/details — response with answers."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/responses/{response_id}/details",
            params={
                "page_ids": ",".join(page_ids) if page_ids else None,
                "question_ids": ",".join(question_ids) if question_ids else None,
                "simple": "true" if simple else None,
            },
        )
        return resp.json()

    def delete_response(self, survey_id: str, response_id: str) -> None:
        """DELETE /surveys/{survey_id}/responses/{response_id} — delete a response."""
        self._request("DELETE", f"/surveys/{survey_id}/responses/{response_id}")

    # ==================================================================
    # COLLECTORS
    # ==================================================================

    def list_collectors(
        self,
        survey_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> CollectorList:
        """GET /surveys/{survey_id}/collectors — list collectors for a survey."""
        resp = self._request(
            "GET",
            f"/surveys/{survey_id}/collectors",
            params={"page": page, "per_page": per_page},
        )
        return CollectorList.model_validate(resp.json())

    def get_collector(self, collector_id: str) -> Collector:
        """GET /collectors/{collector_id} — retrieve a collector."""
        resp = self._request("GET", f"/collectors/{collector_id}")
        return Collector.model_validate(resp.json())

    def create_collector(self, survey_id: str, payload: dict) -> dict:
        """POST /surveys/{survey_id}/collectors — create a collector."""
        resp = self._request(
            "POST", f"/surveys/{survey_id}/collectors", json=payload
        )
        return resp.json()

    def update_collector(self, collector_id: str, payload: dict) -> dict:
        """PATCH /collectors/{collector_id} — update a collector."""
        resp = self._request(
            "PATCH", f"/collectors/{collector_id}", json=payload
        )
        return resp.json()

    def delete_collector(self, collector_id: str) -> None:
        """DELETE /collectors/{collector_id} — delete a collector."""
        self._request("DELETE", f"/collectors/{collector_id}")

    # ------------------------------------------------------------------
    # Collector Messages
    # ------------------------------------------------------------------

    def list_collector_messages(
        self,
        collector_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> CollectorMessageList:
        """GET /collectors/{collector_id}/messages — list messages."""
        resp = self._request(
            "GET",
            f"/collectors/{collector_id}/messages",
            params={"page": page, "per_page": per_page},
        )
        return CollectorMessageList.model_validate(resp.json())

    def create_collector_message(
        self, collector_id: str, payload: dict
    ) -> CollectorMessage:
        """POST /collectors/{collector_id}/messages — create a message."""
        resp = self._request(
            "POST", f"/collectors/{collector_id}/messages", json=payload
        )
        return CollectorMessage.model_validate(resp.json())

    def send_collector_message(
        self,
        collector_id: str,
        message_id: str,
        scheduled_date: str | None = None,
    ) -> dict:
        """POST /collectors/{collector_id}/messages/{message_id}/send — send a message."""
        payload: dict = {}
        if scheduled_date:
            payload["scheduled_date"] = scheduled_date
        resp = self._request(
            "POST",
            f"/collectors/{collector_id}/messages/{message_id}/send",
            json=payload if payload else None,
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Collector Recipients
    # ------------------------------------------------------------------

    def list_collector_recipients(
        self,
        collector_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> RecipientList:
        """GET /collectors/{collector_id}/recipients — list recipients."""
        resp = self._request(
            "GET",
            f"/collectors/{collector_id}/recipients",
            params={"page": page, "per_page": per_page},
        )
        return RecipientList.model_validate(resp.json())

    # ==================================================================
    # WEBHOOKS
    # ==================================================================

    def list_webhooks(
        self, *, page: int = 1, per_page: int = 50
    ) -> WebhookList:
        """GET /webhooks — list all webhooks."""
        resp = self._request(
            "GET", "/webhooks", params={"page": page, "per_page": per_page}
        )
        return WebhookList.model_validate(resp.json())

    def get_webhook(self, webhook_id: str) -> Webhook:
        """GET /webhooks/{webhook_id} — retrieve a webhook."""
        resp = self._request("GET", f"/webhooks/{webhook_id}")
        return Webhook.model_validate(resp.json())

    def create_webhook(self, payload: dict) -> Webhook:
        """POST /webhooks — create a new webhook."""
        resp = self._request("POST", "/webhooks", json=payload)
        return Webhook.model_validate(resp.json())

    def update_webhook(self, webhook_id: str, payload: dict) -> Webhook:
        """PATCH /webhooks/{webhook_id} — update a webhook."""
        resp = self._request("PATCH", f"/webhooks/{webhook_id}", json=payload)
        return Webhook.model_validate(resp.json())

    def delete_webhook(self, webhook_id: str) -> None:
        """DELETE /webhooks/{webhook_id} — delete a webhook."""
        self._request("DELETE", f"/webhooks/{webhook_id}")

    # ==================================================================
    # CONTACTS
    # ==================================================================

    def list_contacts(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        status: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        search_by: str | None = None,
        search: str | None = None,
    ) -> ContactList:
        """GET /contacts — list contacts."""
        resp = self._request(
            "GET",
            "/contacts",
            params={
                "page": page,
                "per_page": per_page,
                "status": status,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "search_by": search_by,
                "search": search,
            },
        )
        return ContactList.model_validate(resp.json())

    def get_contact(self, contact_id: str) -> Contact:
        """GET /contacts/{contact_id} — retrieve a contact."""
        resp = self._request("GET", f"/contacts/{contact_id}")
        return Contact.model_validate(resp.json())

    def create_contact(self, payload: dict) -> Contact:
        """POST /contacts — create a new contact."""
        resp = self._request("POST", "/contacts", json=payload)
        return Contact.model_validate(resp.json())

    def update_contact(self, contact_id: str, payload: dict) -> Contact:
        """PATCH /contacts/{contact_id} — update a contact."""
        resp = self._request("PATCH", f"/contacts/{contact_id}", json=payload)
        return Contact.model_validate(resp.json())

    def delete_contact(self, contact_id: str) -> None:
        """DELETE /contacts/{contact_id} — delete a contact."""
        self._request("DELETE", f"/contacts/{contact_id}")

    # ==================================================================
    # CONTACT LISTS
    # ==================================================================

    def list_contact_lists(
        self, *, page: int = 1, per_page: int = 50
    ) -> ContactGroupList:
        """GET /contact_lists — list contact lists."""
        resp = self._request(
            "GET", "/contact_lists", params={"page": page, "per_page": per_page}
        )
        return ContactGroupList.model_validate(resp.json())

    def get_contact_list(self, list_id: str) -> ContactGroup:
        """GET /contact_lists/{list_id} — retrieve a contact list."""
        resp = self._request("GET", f"/contact_lists/{list_id}")
        return ContactGroup.model_validate(resp.json())

    def create_contact_list(self, name: str) -> ContactGroup:
        """POST /contact_lists — create a new contact list."""
        resp = self._request("POST", "/contact_lists", json={"name": name})
        return ContactGroup.model_validate(resp.json())

    def delete_contact_list(self, list_id: str) -> None:
        """DELETE /contact_lists/{list_id} — delete a contact list."""
        self._request("DELETE", f"/contact_lists/{list_id}")

    def list_contact_list_members(
        self,
        list_id: str,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> ContactList:
        """GET /contact_lists/{list_id}/contacts — list contacts in a list."""
        resp = self._request(
            "GET",
            f"/contact_lists/{list_id}/contacts",
            params={"page": page, "per_page": per_page},
        )
        return ContactList.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_params(params: dict | None) -> dict | None:
    """Removes None-valued keys from a query params dict."""
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}
