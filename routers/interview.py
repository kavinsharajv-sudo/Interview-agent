# routers/interview.py
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from auth.security import User, require_any_hr, require_senior_hr
from pydantic import BaseModel
from graphs.parent_graph import parent_graph as graph 
from langgraph.types import Command

router = APIRouter()

# ── Hardcoded resume paths ─────────────────────────────────────────────────
RESUME_PATHS = [
    "resumes/Kavinsharaj_GenAI_Engineer.pdf",
    "resumes/priya_sharma_resume.pdf",
    "resumes/arjun_mehta_resume.pdf",
]

# ── Request / Response models ──────────────────────────────────────────────

class StartRequest(BaseModel):
    job_description: str


class ApproveRequest(BaseModel):
    approved_emails: list[str]



def get_run_status(graph, thread_id: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        if not state.values:
            return "not_found"
        if state.values.get("error"):
            return "error"
        if state.next and "approval_gate_1" in state.next:
            return "paused_approval"
        if not state.next:
            return "completed"
        return "running"
    except Exception:
        return "not_found"


def clean_candidates(candidates: list) -> list:
    """Remove raw_text before sending to client."""
    return [
        {
            "rank":      i + 1,
            "name":      c["name"],
            "email":     c["email"],
            "score":     c["score"],
            "rationale": c["rationale"],
        }
        for i, c in enumerate(candidates)
    ]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/start")
def start_pipeline(body: StartRequest, current_user: User = Depends(require_any_hr)):
    """
    Accepts job description.
    Uses hardcoded resume paths.
    Runs ResumeScreener and pauses at approval gate.
    Returns thread_id and ranked candidates.
    """
    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "resume_paths":        RESUME_PATHS,
        "job_description":     body.job_description,
        "ranked_candidates":   [],
        "approved_candidates": [],
        "child_thread_ids":    {},
        "scheduled_meetings":  [],
        "processed_reply_keys": [],
        "error":               None,
    }

    ranked_candidates = []
    screener_error = None

    try:
        for event in graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():

                if node_name == "screen_resumes":
                    ranked_candidates = node_output.get("ranked_candidates", [])
                    screener_error = node_output.get("error")

                if node_name == "__interrupt__":
                    pass   # graph paused — we just let the loop end

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if screener_error:
        raise HTTPException(status_code=500, detail=screener_error)

    if not ranked_candidates:
        raise HTTPException(status_code=500, detail="Screener returned no candidates")

    return {
        "thread_id":         thread_id,
        "status":            "paused_approval",
        "message":           "Resumes screened. Waiting for HR approval.",
        "ranked_candidates": clean_candidates(ranked_candidates),
    }


@router.get("/status/{thread_id}")
def get_status(thread_id: str, request: Request):
    """
    Returns current state of a pipeline run.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state  = graph.get_state(config)
        values = state.values
    except Exception:
        raise HTTPException(status_code=404, detail="Run not found")

    if not values:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "thread_id":           thread_id,
        "status":              get_run_status(graph, thread_id),
        "ranked_candidates":   clean_candidates(values.get("ranked_candidates", [])),
        "approved_candidates": values.get("approved_candidates", []),
        "sent_emails":         values.get("sent_emails", []),
        "scheduled_meetings":  values.get("scheduled_meetings", []),
        "error":               values.get("error"),
    }


@router.post("/approve/{thread_id}")
def approve_candidates(
    thread_id: str,
    request:   ApproveRequest,
    req:       Request,
):
    """
    HR submits approved emails.
    Resumes graph — runs EmailComposer and send_emails.
    """
    # graph is imported at the top, no need to get it from the request
    config = {"configurable": {"thread_id": thread_id}}

    # Validate state
    status = get_run_status(graph, thread_id)

    if status == "not_found":
        raise HTTPException(status_code=404, detail="Run not found")

    if status != "paused_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not waiting for approval. Current status: {status}"
        )

    if not request.approved_emails:
        raise HTTPException(status_code=400, detail="approved_emails cannot be empty")

    sent_emails = []
    error       = None

    try:
        for event in graph.stream(
            Command(resume={"approved": request.approved_emails}),
            config=config
        ):
            for node_name, node_output in event.items():

                if node_name == "compose_emails":
                    if node_output.get("error"):
                        error = node_output["error"]

                if node_name == "send_emails":
                    sent_emails = node_output.get("sent_emails", [])
                    if node_output.get("error"):
                        error = node_output["error"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if error:
        raise HTTPException(status_code=500, detail=error)

    return {
        "thread_id":       thread_id,
        "status":          "completed",
        "message":         f"Emails sent to {len(sent_emails)} candidate(s).",
        "approved_emails": request.approved_emails,
        "sent_emails":     sent_emails,
    }


@router.post("/monitor-replies/{thread_id}")
def monitor_replies(
    thread_id: str,
    current_user: User = Depends(require_senior_hr),
):
    """Poll approved candidates' replies once and schedule validated meeting times."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        values = state.values
    except Exception:
        raise HTTPException(status_code=404, detail="Run not found")

    if not values:
        raise HTTPException(status_code=404, detail="Run not found")
    if not values.get("approved_candidates"):
        raise HTTPException(status_code=400, detail="No approved candidates for this run")

    outcomes = []
    try:
        for event in graph.stream(Command(goto="monitor_replies"), config=config):
            node_output = event.get("monitor_replies")
            if node_output is not None:
                if node_output.get("error"):
                    raise HTTPException(status_code=400, detail=node_output["error"])
                outcomes = node_output.get("scheduled_meetings", [])
    except Exception as error:
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(status_code=500, detail=f"Reply monitoring failed: {error}")

    return {
        "thread_id": thread_id,
        "outcomes": outcomes,
    }
