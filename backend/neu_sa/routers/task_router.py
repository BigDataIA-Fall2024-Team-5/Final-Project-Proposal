from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.runnables import RunnableLambda
from neu_sa.agents.task_detection import TaskDetectionAgent
from neu_sa.agents.course_description import CourseDescriptionTool
from neu_sa.agents.sql_agent import SQLAgent
from neu_sa.agents.response_construction import ResponseConstructionAgent
from typing import Annotated, Literal
from typing_extensions import TypedDict

# Define state
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Initialize agents
task_detection_agent = TaskDetectionAgent()
course_description_tool = CourseDescriptionTool()
sql_agent = SQLAgent()
response_construction_agent = ResponseConstructionAgent()

# Create router
task_router = APIRouter()

# Initialize LangGraph
graph = StateGraph(State)

# Add nodes
def task_detection(state: State) -> dict[str, list[AIMessage]]:
    """Task detection node."""
    query = state["messages"][-1].content
    task = task_detection_agent.detect_task(query)
    return {
        "messages": [
            AIMessage(
                content="",
                additional_kwargs={"task": task},
            )
        ]
    }

def course_description_node(state: State) -> dict[str, list[ToolMessage]]:
    """Fetch course description."""
    query = state["messages"][-1].content
    results = course_description_tool.fetch_course_description(query)
    return {
        "messages": [
            ToolMessage(
                content=f"Course Description Results: {results}",
            )
        ]
    }

def sql_agent_node(state: State) -> dict[str, list[ToolMessage]]:
    """Execute SQL query."""
    query = state["messages"][-1].content
    schema = "..."  # Fetch schema as needed
    sql_query = sql_agent.generate_query(query, schema)
    results = sql_agent.sql_query_tool(sql_query)
    return {
        "messages": [
            ToolMessage(
                content=f"SQL Query Results: {results}",
            )
        ]
    }

def response_construction_node(state: State) -> dict[str, list[AIMessage]]:
    """Construct the final response."""
    task = state["messages"][-1].additional_kwargs.get("task")
    results = [
        message.content for message in state["messages"][:-1] if isinstance(message, ToolMessage)
    ]
    response = response_construction_agent.construct_response(task, results)
    return {
        "messages": [
            AIMessage(
                content=response,
            )
        ]
    }

# Define conditional edge to route based on task
def task_router_edge(state: State) -> Literal["course_description", "sql_agent", "final_answer"]:
    task = state["messages"][-1].additional_kwargs.get("task")
    if task == "course description":
        return "course_description"
    elif task == "sql query":
        return "sql_agent"
    return "final_answer"

# Add nodes to graph
graph.add_node("task_detection", task_detection)
graph.add_node("course_description", course_description_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("final_answer", response_construction_node)

# Define entry point
graph.set_entry_point("task_detection")

# Add edges
graph.add_conditional_edges("task_detection", task_router_edge)
graph.add_edge("course_description", "task_detection")
graph.add_edge("sql_agent", "task_detection")
graph.add_edge("final_answer", END)

# Compile the graph
app_graph = graph.compile()

# API Endpoint
@task_router.post("/detect_task")
def detect_task(query: str):
    """API endpoint to handle user queries."""
    state = {
        "messages": [
            AIMessage(content=query),
        ]
    }
    final_state = app_graph.invoke(state)
    return {"response": final_state["messages"][-1].content}
