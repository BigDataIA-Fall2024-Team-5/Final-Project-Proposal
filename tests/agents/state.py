from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.agents import AgentAction
import operator

class AgentState(TypedDict):
    """
    Represents the state of a task in the graph execution process.
    """
    query: str
    messages: Annotated[List[BaseMessage], operator.add]
    query_type: str
    course_description_keywords: List[str]
    generated_query: str
    course_description_results: List[Dict[str, Any]]
    sql_results: List[Dict[str, Any]]
    final_response: str
    visited_nodes: Annotated[List[str], operator.add]
    intermediate_steps: Annotated[List[tuple[AgentAction, str]], operator.add]

def create_agent_state(query: str) -> AgentState:
    """
    Creates and initializes an AgentState instance.
    """
    return AgentState(
        query=query,
        messages=[HumanMessage(content=query)],
        query_type="",
        course_description_keywords=[],
        generated_query="",
        course_description_results=[],
        sql_results=[],
        final_response="",
        visited_nodes=[],
        intermediate_steps=[]
    )