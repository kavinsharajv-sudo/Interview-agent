# state.py
from __future__ import annotations
from typing import TypedDict, Annotated
import operator
from langgraph.graph import MessagesState


class CandidateScore(TypedDict):
    name:      str
    email:     str
    score:     float
    rationale: str
    raw_text:  str


class EmailDraft(TypedDict):
    to:      str
    subject: str
    body:    str


class SentEmail(TypedDict):
    to:         str
    message_id: str


# ── Parent state — shared across all candidates ────────────────────────────
class ParentState(MessagesState):
    resume_paths:        list[str]
    job_description:     str
    ranked_candidates:   list[CandidateScore]
    approved_candidates: list[str]
    child_thread_ids:    dict[str, str]   # email → child thread_id
    scheduled_meetings:  list[dict]
    processed_reply_keys: list[str]
    error:               str | None


# ── Child state — one per candidate ───────────────────────────────────────
class ChildState(MessagesState):
    candidate_name:   str
    candidate_email:  str
    candidate_resume: str
    job_description:  str
    email_draft:      dict
    sent_email:       dict
    error:            str | None


# keep InterviewState as alias so nothing breaks during transition
InterviewState = ParentState
