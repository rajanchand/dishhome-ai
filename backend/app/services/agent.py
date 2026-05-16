import operator
from typing import Annotated, Any, Sequence, TypedDict, Union

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.config import settings

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    customer_id: str
    language: str

def get_model():
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_host,
        temperature=0,
    )

def call_model(state: AgentState):
    messages = state["messages"]
    model = get_model()
    response = model.invoke(messages)
    return {"messages": [response]}

def create_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", call_model)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    
    return workflow.compile()

# Example system prompt for DishHome AI
SYSTEM_PROMPT = """You are Khushi, the intelligent voice assistant for DishHome ISP.
Your goal is to help customers with router troubleshooting, billing, and technical support.
You are bilingual in Nepali and English. Always respond in the language the customer uses.

If you don't know something, offer to transfer them to a human agent.
Keep your responses concise and friendly (voice-optimized).
"""

def get_initial_state(customer_id: str, language: str = "ne") -> AgentState:
    return {
        "messages": [SystemMessage(content=SYSTEM_PROMPT)],
        "customer_id": customer_id,
        "language": language,
    }
