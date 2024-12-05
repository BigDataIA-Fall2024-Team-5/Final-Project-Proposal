from langgraph.graph import StateGraph, END
from state import AgentState, create_agent_state

def task_detection_node(state: AgentState) -> AgentState:
    """task_detection_node"""
    from task_detection import TaskDetectionAgent
    agent = TaskDetectionAgent()
    return agent.detect_task(state)

def general_information_node(state: AgentState) -> AgentState:
    from general_information_agent import GeneralInformationAgent
    agent = GeneralInformationAgent()
    return agent.search(state)

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

def user_course_agent_node(state: AgentState) -> AgentState:
    """user_course_agent_node"""
    from user_course_agent import UserCourseAgent
    agent = UserCourseAgent()
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
graph.add_node("general_information", general_information_node) 
graph.add_node("course_description", course_description_node)
graph.add_node("sql_agent", sql_agent_node)
graph.add_node("user_course_agent", user_course_agent_node)
graph.add_node("response_construction", response_construction_node)

graph.set_entry_point("task_detection")
graph.add_conditional_edges("task_detection", routing_decision, {"course_description", "sql_agent", "user_course", "response_construction"})
graph.add_conditional_edges("general_information", routing_decision, {"general_information","response_construction"})
graph.add_conditional_edges("sql_agent", routing_decision, {"course_description","user_course_agent","response_construction"})
graph.add_conditional_edges("user_course_agent", routing_decision, {"sql_agent", "response_construction"})
graph.add_conditional_edges("course_description", routing_decision, {"sql_agent","response_construction"})




graph.add_edge("response_construction", END)

compiled_graph = graph.compile()

def test_runner(query: str,user_id: int):
    state = create_agent_state(query,user_id)
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
    if final_state.get("general_information_results"):
        print("\n--- General Information Results ---")
        for result in final_state["general_information_results"]:
            print(f"Score: {result['score']}")
    if final_state.get("sql_results"):
        print("\n--- SQL Query Results ---")
        print(final_state["sql_results"])
    if final_state.get("user_completed_courses"):
        print("\n--- user_completed_courses ---")
        print(final_state["user_completed_courses"])
    if final_state.get("user_eligibility"):
        print("\n--- user_eligibility ---")
        print(final_state["user_eligibility"])

    if final_state.get("final_response"):
        print("\n--- Final Response ---")
        print(final_state["final_response"])

if __name__ == "__main__":
    test_query = "TELE 7990 is this a core subject for for Telecommunication Networks"
    test_user_id = 1
    test_runner(test_query,test_user_id)