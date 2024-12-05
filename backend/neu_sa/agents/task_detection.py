import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from neu_sa.agents.state import AgentState

load_dotenv()

class TaskDetectionAgent:
    def __init__(self, model="gpt-4"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a task detection agent responsible for analyzing user queries "
                "and determining which tools should be used to answer them. Your responsibilities are:\n"
                "1. Determine which of the following nodes need to be visited:\n"
                "   - 'course_description': For queries focused on conceptual matches with courses (e.g., 'Suggest me a course with Python').\n"
                "   - 'sql_agent': For queries requiring precise data retrieval from a SQL database, especially for:\n"
                "       - Prerequisite and corequisite information for courses (e.g., 'What are the prerequisites for INFO 7110?').\n"
                "       - Details about specific courses, course code, program, classes ,core , electives (e.g., timings, description, profressors).\n"
                "       - Check a course if it is core, elective. check program requirements (if its for user then goto user_course_agent after sql_agent)\n"
                "   - 'user_course_agent': For queries about a specific user's course information, eligibility, or academic history, such as:\n"
                "       - It gets information about the user (user's enrolled program, completed courses, grade, campus, college, credit requirement for graduation).\n"
                "   - 'general_information': Queries that require information from general resources (e.g., 'What are the on-campus job opportunities').\n"
                "   - 'response_construction': Queries that do not require analysis or data retrieval.\n"
                "2. Handling queries about course eligibility or prerequisites:\n"
                "   - First 'sql_agent' to retrieve prerequisite/corequisite Then 'user_course_agent' to check the user's completed courses and academic history.\n"
                "3. Handling queries about user program:\n"
                "   - First 'user_course_agent' to retrieve user information Then 'sql_agent' to get more information using user details.\n"
                "4. Generate relevant keywords for course description searches when needed:\n"
                "   - Focus on detailed topics, related technologies, and domain-specific skills.\n"
                "   - Examples:\n"
                "     - For 'ML', generate: ['Machine Learning', 'Artificial Intelligence', 'Deep Learning', 'Python', 'TensorFlow'].\n"
                "     - For 'Cloud Computing', generate: ['Cloud Computing', 'AWS', 'Azure', 'Kubernetes'].\n"
                "4. Output a JSON with:\n"
                "   - 'nodes_to_visit': List of nodes to visit ('course_description', 'general_information', 'sql_agent', 'user_course_agent', or a combination).\n"
                "   - 'course_description_keywords': List of keywords relevant to course descriptions (if applicable).\n"
                "   - 'explanation': Brief explanation of the decision."
            ),
            ("user", "{query}"),
        ])


    def detect_task(self, state: AgentState) -> AgentState:
        
        print("DEBUG: Executing task detection agent") #debug

        input_message = {"query": state["query"]}
        response = self.prompt | self.llm
        try:
            result = response.invoke(input_message)
            result_dict = json.loads(result.content)
            if not all(key in result_dict for key in ["nodes_to_visit", "explanation"]):
                raise ValueError("Incomplete response from LLM.")
            
            state["nodes_to_visit"] = result_dict["nodes_to_visit"]

            print(f"DEBUG: task detection agent: {state["nodes_to_visit"]}") #debug

            state["visited_nodes"].append("task_detection")
            state["course_description_keywords"].extend(result_dict.get("course_description_keywords", []))
            state["messages"].extend([
                HumanMessage(content=state["query"]).model_dump(),
                AIMessage(content=f"Nodes to visit: {', '.join(result_dict['nodes_to_visit'])}").model_dump()
            ])
        except Exception as e:
            state["error"] = f"Failed to detect task: {e}"
        
        return state