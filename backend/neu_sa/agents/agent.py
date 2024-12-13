from langgraph.graph import StateGraph, END
from neu_sa.agents.state import AgentState, create_agent_state

def task_detection_node(state: AgentState) -> AgentState:
    """task_detection_node"""
    from neu_sa.agents.task_detection import TaskDetectionAgent
    agent = TaskDetectionAgent()
    return agent.detect_task(state)

def general_information_node(state: AgentState) -> AgentState:
    from neu_sa.agents.general_information_agent import GeneralInformationAgent
    agent = GeneralInformationAgent()
    return agent.search(state)

def course_description_node(state: AgentState) -> AgentState:
    """course_description_node"""
    from neu_sa.agents.course_description_agent import CourseDescriptionAgent
    agent = CourseDescriptionAgent()
    return agent.search(state)

def sql_agent_node(state: AgentState) -> AgentState:
    """sql_agent_node"""
    from neu_sa.agents.sql_agent import SQLAgent
    agent = SQLAgent()
    return agent.process(state)

def user_course_agent_node(state: AgentState) -> AgentState:
    """user_course_agent_node"""
    from neu_sa.agents.user_course_agent import UserCourseAgent
    agent = UserCourseAgent()
    return agent.process(state)

def response_construction_node(state: AgentState) -> AgentState:
    """response_construction_node"""
    from neu_sa.agents.response_construction import ResponseConstructionAgent
    agent = ResponseConstructionAgent()
    return agent.construct_response(state)

def routing_decision(state: AgentState):
    nodes = state.get("nodes_to_visit", [])
    if isinstance(nodes, list) and nodes:
        print(f"Routing logic: {nodes}")
        next_node = nodes.pop(0)
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
