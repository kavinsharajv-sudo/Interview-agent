# graphs/child_graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import ChildState
from agents.email_composer import email_composer_node
from agents.send_email import send_email_node


def build_child_graph():
    builder = StateGraph(ChildState)

    builder.add_node("compose_email", email_composer_node)
    builder.add_node("send_email",    send_email_node)

    builder.set_entry_point("compose_email")

    builder.add_conditional_edges(
        "compose_email",
        lambda state: END if state.get("error") else "send_email"
    )

    builder.add_edge("send_email", END)

    return builder.compile(checkpointer=MemorySaver())
