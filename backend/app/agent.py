import operator
import re
from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
import logging
from sqlalchemy import select, or_

logger = logging.getLogger(__name__)

# ── Tool input validation ──
# The LLM constructs these strings, but the LLM is *not* an authenticated user;
# treat its output as untrusted input and enforce the same shape we'd expect
# from a request path parameter.
_ONT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_QUERY_RE = re.compile(r"^[A-Za-z0-9._@+-]{1,64}$")


@tool
async def check_router_status(ont_id: str) -> str:
    """Check the status of a DishHome ONT router device by its ID. Use this if the user asks why their internet is down."""
    ont_id = (ont_id or "").strip()
    if not _ONT_ID_RE.match(ont_id):
        return "Invalid ONT ID."

    # Call the DB layer directly — going through HTTP would require minting a
    # privileged token for the LLM (which can be steered by prompt injection)
    # and would loop back through the request pipeline.
    from app.database import async_session_maker
    from app.models.customer import ONTStatus as ONTStatusModel
    if async_session_maker is None:
        return "Database unavailable."
    try:
        async with async_session_maker() as db:
            result = await db.execute(select(ONTStatusModel).where(ONTStatusModel.ont_id == ont_id))
            row = result.scalar_one_or_none()
        if not row:
            return f"Router {ont_id} not found."
        return (
            f"Router {ont_id} is {'Online' if row.online else 'Offline'}. "
            f"Outage in area: {row.area_outage}. Uptime: {row.uptime_hours} hours."
        )
    except Exception as e:
        logger.error("Tool check_router_status failed: %s", e)
        return "Failed to check router status."


@tool
async def lookup_customer(query: str) -> str:
    """Lookup a DishHome customer by their customer ID, mobile number, or smartcard number."""
    query = (query or "").strip()
    if not _QUERY_RE.match(query):
        return "Invalid lookup query."

    from app.database import async_session_maker
    from app.models.customer import Customer as CustomerModel
    if async_session_maker is None:
        return "Database unavailable."
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(CustomerModel).where(
                    or_(
                        CustomerModel.customer_id == query,
                        CustomerModel.mobile == query,
                        CustomerModel.smartcard == query,
                    )
                )
            )
            cust = result.scalar_one_or_none()
        if not cust:
            return "Customer not found."
        # Avoid surfacing the smartcard number / mobile to the LLM context;
        # the agent only needs identity + service-relevant fields to help.
        return (
            f"Customer Found: Name: {cust.name}, Package: {cust.package}, "
            f"ONT ID: {cust.ont_id}, Balance: NPR {cust.balance_npr}, Status: {cust.status}"
        )
    except Exception as e:
        logger.error("Tool lookup_customer failed: %s", e)
        return "Failed to lookup customer."

tools = [check_router_status, lookup_customer]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    call_id: str

async def process_llm(state: AgentState):
    # Resolve Ollama config through the runtime-config layer so a
    # super_admin can repoint the agent to a different host/model from the
    # Settings UI without a redeploy.
    from app.database import async_session_maker
    from app.services.runtime_config import get_effective
    from app.config import settings as _settings

    model = _settings.ollama_model
    host = _settings.ollama_host
    if async_session_maker is not None:
        try:
            async with async_session_maker() as db:
                model = await get_effective(db, "ollama_model") or model
                host = await get_effective(db, "ollama_host") or host
        except Exception as e:
            logger.warning("runtime_config lookup failed, using env defaults: %s", e)

    try:
        llm = ChatOllama(model=model, base_url=host)
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content="I'm sorry, my cognitive systems are currently offline. Please try again later.")]}

async def tool_node(state: AgentState):
    """Execute tools."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM didn't call a tool, do nothing
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"messages": []}
        
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        logger.info(f"Executing tool {tool_name} with args {tool_args}")
        
        tool_func = {t.name: t for t in tools}.get(tool_name)
        if tool_func:
            result = await tool_func.ainvoke(tool_args)
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
        else:
            tool_messages.append(ToolMessage(content=f"Tool {tool_name} not found", tool_call_id=tool_call["id"]))
            
    return {"messages": tool_messages}

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("llm", process_llm)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("llm")
workflow.add_conditional_edges("llm", should_continue)
workflow.add_edge("tools", "llm")

app_graph = workflow.compile()

async def run_conversation_agent(call_id: str, text: str) -> str:
    """Runs the LangGraph agent for a single turn."""
    system_prompt = SystemMessage(content="You are Khushi, a helpful DishHome AI support agent. Be concise and speak naturally.")
    messages = [system_prompt, HumanMessage(content=text)]
    
    try:
        final_state = await app_graph.ainvoke({"messages": messages, "call_id": call_id})
        return final_state["messages"][-1].content
    except Exception as e:
        logger.error(f"Error running agent for {call_id}: {e}")
        return "I encountered an error processing your request."
