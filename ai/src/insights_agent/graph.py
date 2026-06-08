from functools import lru_cache
from insights_agent.config import get_settings
from insights_agent.state import AgentState
from insights_agent.tools import TOOLS
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM = """You are a data analyst for the Online Retail pipeline (PostgreSQL).
Use tools to answer; never invent numbers.
- KPIs (total revenue, top 10, monthly trend) → run_gold_query
- Custom analytics → always call get_semantic_layer first, then run_sql_readonly
- Definitions only → get_semantic_layer
- sales_clean has customer_id_hash only; column customer_id does NOT exist — never use customer_id
- If run_sql_readonly returns error query_failed, read the message, fix the SQL, and retry once
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
        msgs = [SystemMessage(content=SYSTEM), HumanMessage(content=state["question"])]

        msgs = msgs + state.get("messages", [])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    def answer(state: AgentState):
        prompt = (
            "Summarize the tool results for the user. "
            "Use only facts from tool output. Mention SQL when present.\n\n"
            f"Question: {state['question']}\n\n"
            f"Tool trace:\n{state['messages']}"
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"final_answer": resp.content}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tools", tool_node)
    g.add_node("answer", answer)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "answer"})
    g.add_edge("tools", "agent")
    g.add_edge("answer", END)
    return g.compile()

def run_question(question: str) -> AgentState:
    graph = build_graph()
    return graph.invoke(
        {"question": question, "messages": [], "final_answer": None},
        config={"recursion_limit": 15},
    )