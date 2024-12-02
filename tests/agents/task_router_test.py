from langgraph.graph import StateGraph, END
from state import AgentState, create_agent_state

def task_detection_node(state: AgentState) -> AgentState:
    """task_detection_node"""
    from task_detection import TaskDetectionAgent
    agent = TaskDetectionAgent()
    return agent.detect_task(state)

def course_description_node(state: AgentState) -> AgentState:
    """course_description_node"""
    from course_description_agent import CourseDescriptionAgent
    agent = CourseDescriptionAgent()
    return agent.search(state)

def sql_agent_node(state: AgentState) -> AgentState:
    """sql_agent_node"""
    from sql_agent import SQLAgent
    agent = SQLAgent()
    return agent.process(state)

def response_construction_node(state: AgentState) -> AgentState:
    """response_construction_node"""
    from response_construction import ResponseConstructionAgent
    agent = ResponseConstructionAgent()
    return agent.construct_response(state)

def routing_decision(state: AgentState):
    if state["nodes_to_visit"]:
        print(f"Routing logic: {state["nodes_to_visit"]}")
        next_node = state["nodes_to_visit"].pop(0)
        return next_node
    return "response_construction"

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("task_detection", task_detection_node)
graph.add_node("course_description", course_description_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("response_construction", response_construction_node)

graph.set_entry_point("task_detection")
graph.add_conditional_edges("task_detection", routing_decision, {"course_description","sql_agent","response_construction"})
graph.add_conditional_edges("course_description", routing_decision, {"sql_agent","response_construction"})
graph.add_conditional_edges("sql_agent", routing_decision, {"course_description","response_construction"})
graph.add_edge("response_construction", END)

compiled_graph = graph.compile()

def test_runner(query: str):
    state = create_agent_state(query)
    final_state = compiled_graph.invoke(state)

    print("\n--- Task Execution Results ---")
    print(f"Visited Nodes: {final_state['visited_nodes']}")
    if final_state.get("nodes_to_visit"):
        print("\n--- Nodes to Visit ---")
        print(final_state["nodes_to_visit"])
    if final_state.get("course_description_keywords"):
        print("\n--- Course Description Keywords ---")
        print(final_state["course_description_keywords"])
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
    test_query = "What courses on BigData Analytics are available in Spring 2025"
    test_runner(test_query)