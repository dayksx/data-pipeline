from functools import lru_cache
from insights_agent.config import get_settings
from insights_agent.state import AgentState
from insights_agent.tools import TOOLS
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

SYSTEM = """You are a data analyst for the Online Retail pipeline (PostgreSQL).
Use tools to answer; never invent numbers.

Routing:
- KPIs (total revenue, top 10, monthly trend) → run_gold_query
- Custom analytics → get_semantic_layer first, then run_sql_readonly
- Schema / column definitions only → get_semantic_layer
- WHY / HOW / anomalies / patterns / B2B context / data quality → search_analyses
- Official numbers always from SQL — never from search_analyses alone
- You may combine tools: e.g. search_analyses for context + run_gold_query for the figure

Rules:
- sales_clean has customer_id_hash only; customer_id does NOT exist
- If run_sql_readonly returns query_failed, read the message, fix SQL, retry once
- When citing RAG results, mention the source file (field: source)

Currency: GBP. Data: Jan 2010 – Dec 2011 (Dec 2011 partial)."""


@lru_cache
def build_graph():
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(TOOLS)
    tool_node = ToolNode(TOOLS)

    def agent(state: AgentState):
        msgs = [SystemMessage(content=SYSTEM)] + state.get("messages", [])

        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def answer(state: AgentState):
        messages = state.get("messages", [])
        used_tools = any(getattr(m, "type", None) == "tool" for m in messages)

        if not used_tools:
            return {"final_answer": messages[-1].content if messages else "(no answer)"}

        system_prompt = SystemMessage(content=(
            "Summarize the tool results for the user. "
            "Use only facts from tool output. Mention SQL when relevant.1"
            "If you used search_analyses, mention the query and the chunks returned."            ))
        
        resp = llm.invoke([system_prompt, *messages])

        return {"final_answer": resp.content}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tools", tool_node)
    g.add_node("answer", answer)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "answer"})
    g.add_edge("tools", "agent")
    g.add_edge("answer", END)
    return g.compile(checkpointer=MemorySaver())

def run_question(question: str, thread_id: str) -> AgentState:
    graph = build_graph()
    return graph.invoke(
        {
            "messages": [HumanMessage(content=question)], 
            "final_answer": None},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 15,
            },
    )