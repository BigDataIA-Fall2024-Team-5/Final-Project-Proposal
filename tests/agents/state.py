from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
import operator

class AgentState(TypedDict):
    """
    Represents the state of a task in the graph execution process.
    """
    query: str
    messages: Annotated[List[BaseMessage], operator.add]
    nodes_to_visit: List[str]
    course_description_keywords: List[str]
    generated_query: str
    course_description_results: List[Dict[str, Any]]
    sql_results: List[Dict[str, Any]]
    general_information_results: List[Dict[str, Any]]   
    final_response: str
    visited_nodes: List[str]

def create_agent_state(query: str) -> AgentState:
    """
    Creates and initializes an AgentState instance.
    """
    return AgentState(
        query=query,
        messages=[HumanMessage(content=query)],
        nodes_to_visit=[],
        course_description_keywords=[],
        generated_query="",
        course_description_results=[],
        sql_results=[],
        general_information_results=[], 
        final_response="",
        visited_nodes=[]
    )