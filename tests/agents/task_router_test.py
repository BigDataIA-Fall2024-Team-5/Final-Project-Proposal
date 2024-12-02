from langgraph.graph import StateGraph, END
from state import AgentState
from langchain_core.messages import HumanMessage, AIMessage

def task_detection_node(state: AgentState) -> AgentState:
    from task_detection import TaskDetectionAgent
    agent = TaskDetectionAgent()
    return agent.detect_task(state)

def course_description_node(state: AgentState) -> AgentState:
    from course_description_agent import CourseDescriptionAgent
    agent = CourseDescriptionAgent()
    return agent.search(state)

def sql_agent_node(state: AgentState) -> AgentState:
    from sql_agent import SQLAgent
    agent = SQLAgent()
    return agent.process(state)

def response_construction_node(state: AgentState) -> AgentState:
    from response_construction import ResponseConstructionAgent
    agent = ResponseConstructionAgent()
    return agent.construct_response(state)


def routing_decision(state: AgentState):
    if state["query_type"] == "course_description":
        return "course_description"
    elif state["query_type"] == "sql_agent":
        return "sql_agent"
    elif state["query_type"] == "course_description+sql_agent":
        if "course_description" not in state["visited_nodes"]:
            return "course_description"
        if "sql_agent" not in state["visited_nodes"]:
            return "sql_agent"
        return "response_construction"
    else:
        return END

graph = StateGraph(AgentState)
graph.add_node("task_detection", task_detection_node)
graph.add_node("course_description", course_description_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("response_construction", response_construction_node)

graph.set_entry_point("task_detection")
graph.add_conditional_edges("task_detection", routing_decision)
graph.add_edge("course_description", "response_construction")
graph.add_edge("sql_agent", "response_construction")
graph.add_edge("response_construction", END)

compiled_graph = graph.compile()

def test_runner(query: str):
    state = AgentState(query=query)
    final_state = compiled_graph.invoke(state)

    print("\n--- Task Execution Results ---")
    print(f"Visited Nodes: {final_state['visited_nodes']}")
    if final_state.get("course_description_results"):
        print("\n--- Course Description Results ---")
        print(final_state["course_description_results"])
    if final_state.get("generated_query"):
        print("\n--- Generated SQL Query ---")
        print(final_state["generated_query"])
    if final_state.get("sql_results"):
        print("\n--- SQL Query Results ---")
        print(final_state["sql_results"])
    if final_state.get("final_response"):
        print("\n--- Final Response ---")
        print(final_state["final_response"])

if __name__ == "__main__":
    test_query = "What courses on BigData Analytics are available"
    test_runner(test_query)
