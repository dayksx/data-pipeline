from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):

    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    final_answer: str | None

