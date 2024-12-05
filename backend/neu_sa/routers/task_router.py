from fastapi import APIRouter, Depends
from pydantic import BaseModel
from neu_sa.routers.auth import validate_jwt
from neu_sa.agents.state import create_agent_state, AgentState
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage
from typing import List

# Define the router
task_router = APIRouter()

# Task router input model
class TaskQuery(BaseModel):
    query: str
    history: List[dict] 

# Inject compiled_graph from the agents module
def get_graph():
    from neu_sa.agents.agent import compiled_graph
    return compiled_graph

@task_router.post("/query")
def process_query(
    task_query: TaskQuery,
    token: dict = Depends(validate_jwt),
    compiled_graph: StateGraph = Depends(get_graph),
):
    """
    Handle incoming user queries by running them through the task detection graph.
    """
    user_id = token["user_id"]  # Extract user ID from token

    # Create an initial state for the query
    state = create_agent_state(
        query=task_query.query,
        user_id=user_id,
        chat_history=task_query.history
    )

    # Convert chat history messages into HumanMessage or AIMessage objects
    state["messages"] = [
        HumanMessage(content=msg["content"]) if msg["role"] == "user" else AIMessage(content=msg["content"])
        for msg in task_query.history
    ]

    # Process the state through the graph
    final_state = compiled_graph.invoke(state)

    # Return the final response
    return {
        "final_response": final_state.get("final_response"),
    }
