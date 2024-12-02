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

# Graph Setup for Testing
graph = StateGraph(AgentState)
graph.add_node("task_detection", task_detection_node)
graph.add_node("course_description", course_description_node)

graph.set_entry_point("task_detection")
graph.add_edge("task_detection", "course_description")
graph.add_edge("course_description", END)

compiled_graph = graph.compile()

# Test Runner
def test_runner(query: str):
    state = AgentState(query=query)
    final_state = compiled_graph.invoke(state)

    print("\n--- Task Execution Results ---")
    if isinstance(final_state, dict):
        if 'visited_nodes' in final_state:
            print(f"Visited Nodes: {final_state['visited_nodes']}")
        if 'course_description_results' in final_state:
            print("\n--- Course Description Results ---")
            print(final_state['course_description_results'])
        if 'query_type' in final_state:
            print("\n--- Detected Query Type ---")
            print(final_state['query_type'])
        if 'course_description_keywords' in final_state:
            print("\n--- Course Description Keywords ---")
            print(final_state['course_description_keywords'])
    else:
        print("Unexpected final state type:", type(final_state))
        print("Final state content:", final_state)

if __name__ == "__main__":
    test_query = "What courses on BigData Analytics are available"
    test_runner(test_query)
