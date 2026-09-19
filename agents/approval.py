# agents/approval.py
from langgraph.types import interrupt
from state import InterviewState


def approval_gate_1(state: InterviewState) -> dict:
    """
    Pauses the graph. Surfaces ranked candidates to HR.
    Resumes when HR calls Command(resume={"approved": [...]})
    """

    # Build a clean display list — no raw_text, just what HR needs to see
    display_candidates = [
        {
            "rank":      i + 1,
            "name":      c["name"],
            "email":     c["email"],
            "score":     c["score"],
            "rationale": c["rationale"],
        }
        for i, c in enumerate(state["ranked_candidates"])
    ]

    # interrupt() pauses the graph here and sends this payload
    # to whoever is listening (your UI, a script, a webhook)
    decision = interrupt({
        "message":    "Review ranked candidates and select who to invite for interview.",
        "candidates": display_candidates,
    })

    # When HR resumes, decision contains {"approved": ["email1", "email2"]}
    approved = decision.get("approved", [])

    if not approved:
        return {"error": "No candidates approved by HR. Pipeline stopped."}

    return {"approved_candidates": approved}
