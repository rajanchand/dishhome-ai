import operator
from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
import logging
import httpx
import json

logger = logging.getLogger(__name__)

# Define Tools
@tool
async def check_router_status(ont_id: str) -> str:
    """Check the status of a DishHome ONT router device by its ID. Use this if the user asks why their internet is down."""
    from app.security import create_access_token
    token = create_access_token({"sub": "admin", "role": "super_admin"})
    
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"/integrations/dishhome/router-status/{ont_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return f"Router {ont_id} is {'Online' if data['online'] else 'Offline'}. Outage in area: {data['area_outage']}. Uptime: {data['uptime_hours']} hours."
            return f"Router {ont_id} not found."
    except Exception as e:
        logger.error(f"Tool check_router_status failed: {e}")
        return "Failed to check router status."

@tool
async def lookup_customer(query: str) -> str:
    """Lookup a DishHome customer by their customer ID, mobile number, or smartcard number."""
    from app.security import create_access_token
    token = create_access_token({"sub": "admin", "role": "super_admin"})
    
    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"/integrations/dishhome/customer/{query}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return f"Customer Found: Name: {data['name']}, Package: {data['package']}, ONT ID: {data['ont_id']}, Balance: NPR {data['balance_npr']}, Status: {data['status']}"
            return "Customer not found."
    except Exception as e:
        logger.error(f"Tool lookup_customer failed: {e}")
        return "Failed to lookup customer."

tools = [check_router_status, lookup_customer]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    call_id: str

async def process_llm(state: AgentState):
    from app.config import settings
    # Ensure Ollama is running. For fallback, we could catch connection errors.
    try:
        llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_host)
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        # Fallback response if Ollama is not running locally
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
