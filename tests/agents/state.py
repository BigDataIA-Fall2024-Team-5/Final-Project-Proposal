from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
import operator

class AgentState(TypedDict):
    """
    Represents the state of a task in the graph execution process.
    """
    query: str
    user_id: int
    messages: Annotated[List[BaseMessage], operator.add]
    nodes_to_visit: List[str]
    course_description_keywords: List[str]
    generated_query: str
    course_description_results: List[Dict[str, Any]]
    sql_results: List[Dict[str, Any]]
    general_information_results: List[Dict[str, Any]]   
    final_response: str
    visited_nodes: List[str]
    course_prerequisites: List[Dict[str, Any]]
    user_completed_courses: List[Dict[str, Any]]
    user_campus: str
    user_eligibility: List[Dict[str, Any]]

def create_agent_state(query: str, user_id: int) -> AgentState:
    """
    Creates and initializes an AgentState instance.
    """
    return AgentState(
        query=query,
        user_id=user_id,
        messages=[HumanMessage(content=query)],
        nodes_to_visit=[],
        course_description_keywords=[],
        generated_query="",
        course_description_results=[],
        sql_results=[],
        general_information_results=[], 
        final_response="",
        visited_nodes=[],
        user_completed_courses=[],
        user_campus="",
        user_eligibility=[]
    )