# graphs/parent_graph.py
import uuid
from langgraph.graph             import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state             import ParentState
from agents.screener   import resume_screener_node
from agents.approval   import approval_gate_1
from agents.reply_scheduler import monitor_replies_node
from graphs.child_graph import build_child_graph


def spawn_children_node(state: ParentState) -> dict:
    """
    Creates one child graph per approved candidate.
    Each child composes and sends one email independently.
    """
    child_graph      = build_child_graph()
    child_thread_ids = {}

    for email in state["approved_candidates"]:

        # find full profile
        candidate = next(
            (c for c in state["ranked_candidates"]
             if c["email"].lower() == email.lower()),
            None
        )

        if not candidate:
            print(f"  Candidate {email} not found")
            continue

        # unique thread_id per candidate
        child_thread_id = f"child-{email}-{uuid.uuid4()}"
        child_config    = {"configurable": {"thread_id": child_thread_id}}

        # child initial state
        child_initial = {
            "candidate_name":   candidate["name"],
            "candidate_email":  candidate["email"],
            "candidate_resume": candidate["raw_text"],
            "job_description":  state["job_description"],
            "email_draft":      {},
            "sent_email":       {},
            "error":            None,
        }

        print(f"\n  Spawning child for: {candidate['name']}")

        # run child — compose email and send it
        for event in child_graph.stream(child_initial, config=child_config):
            for node_name, node_output in event.items():
                if node_name == "compose_email":
                    print(f"    ✓ Email composed for {candidate['name']}")
                if node_name == "send_email":
                    sent = node_output.get("sent_email", {})
                    if sent:
                        print(f"    ✓ Email sent to {candidate['email']}")
                    error = node_output.get("error")
                    if error:
                        print(f"    ✗ Error: {error}")

        child_thread_ids[email] = child_thread_id

    return {"child_thread_ids": child_thread_ids}


def build_parent_graph():
    builder = StateGraph(ParentState)

    builder.add_node("screen_resumes",  resume_screener_node)
    builder.add_node("approval_gate_1", approval_gate_1)
    builder.add_node("spawn_children",  spawn_children_node)
    builder.add_node("monitor_replies", monitor_replies_node)

    builder.set_entry_point("screen_resumes")

    builder.add_conditional_edges(
        "screen_resumes",
        lambda state: END if state.get("error") else "approval_gate_1"
    )
    builder.add_conditional_edges(
        "approval_gate_1",
        lambda state: END if state.get("error") else "spawn_children"
    )

    builder.add_edge("spawn_children", END)
    builder.add_edge("monitor_replies", END)

    return builder.compile(checkpointer=MemorySaver())


parent_graph = build_parent_graph()
