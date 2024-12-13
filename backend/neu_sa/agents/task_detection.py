import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from neu_sa.agents.state import AgentState

load_dotenv()

class TaskDetectionAgent:
    def __init__(self, model="gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a task detection agent responsible for analyzing 'Latest query:' (you must choose nodes_to_visit based on latest query) "
                "and determining which tools should be used to answer them (user chat history to understand context). Your responsibilities are:\n"
                "1. Determine which of the following nodes need to be visited:\n"
                "   - 'course_description': For queries focused on conceptual matches with courses (e.g., 'Suggest me a course with Python').\n"
                "   - 'sql_agent': For queries requiring precise data retrieval from a SQL database, especially for:\n"
                "       - Prerequisite and corequisite information for courses (e.g., 'What are the prerequisites for INFO 7110?').\n"
                "       - Details about specific courses, course code, program ,core , electives \n"
                "       - Check a course if it is core, elective. check program requirements (if its for user then goto user_course_agent after sql_agent)\n"
                "       - Check for class timing, class details specific to campus locations (e.g., timings, description, profressors). \n"
                "   - 'user_course_agent': For queries about user's course information, eligibility, or academic history:\n"
                "       - It has information about the user (user's enrolled program, completed courses, grade, campus, college, credit requirement for graduation).\n"
                "       - If user ask if he is eligible for a course (Mostly used after sql_agent)\n"
                "   - 'general_information': Queries that require information from general resources (e.g., 'What are the on-campus job opportunities').\n"
                "2. Handling queries about course eligibility or prerequisites: (e.g., Can i take those course, Am i elgilbe to do this)\n"
                "   - First 'sql_agent' to retrieve prerequisite for the course Then 'user_course_agent' to check the user's completed courses and academic history.\n"
                "3. Handling queries about user program:\n"
                "   - First 'user_course_agent' to retrieve user information Then 'sql_agent' to get more information using user details.\n"
                "4. Generate relevant keywords for course description searches when needed:\n"
                "   - Focus on detailed topics, related technologies, and domain-specific skills.\n"
                "   - Examples:\n"
                "     - For 'ML', generate: ['Machine Learning', 'Artificial Intelligence', 'Deep Learning', 'Python', 'TensorFlow'].\n"
                "     - For 'Cloud Computing', generate: ['Cloud Computing', 'AWS', 'Azure', 'Kubernetes'].\n"
                "5. Generate a concise and generalized description for general_information (RAG-based searches):\n"
                "   - Focus on summarizing the core intent and broader context of the user's query while removing unnecessary specifics.\n" 
                "   - Ensure the description is structured to aid in linking follow-up questions to the original query context.\n" 
                "   - Examples: For 'What are the on-campus job opportunities?', generate:\n" 
                "       - Generalized Description: 'Details about student employment and on-campus job opportunities at Northeastern University.'\n" 
                "6. Output a JSON with:\n"
                "   - 'nodes_to_visit': List of nodes to visit ('course_description', 'general_information', 'sql_agent', 'user_course_agent', or a combination).\n"
                "   - 'course_description_keywords': List of keywords relevant to course descriptions (if applicable).\n"
                "   - 'general_description': A concise and generalized version of the query that captures its main intent (if applicable).\n"
                "   - 'explanation': Brief explanation of the decision."
                "user chat history: {chat_history}"
            ),
            ("user", "{query}"),
        ])


    def detect_task(self, state: AgentState) -> AgentState:
        
        print("DEBUG: Executing task detection agent") #debug

        input_message = {
            "chat_history": state["chat_history"],
            "query": state["query"],
        }
        response = self.prompt | self.llm

        try:
            result = response.invoke(input_message)
            result_dict = json.loads(result.content)
            if not all(key in result_dict for key in ["nodes_to_visit", "explanation"]):
                raise ValueError("Incomplete response from LLM.")
            
            state["nodes_to_visit"] = result_dict["nodes_to_visit"]
            print(f"DEBUG: Query : {state['query']}") #debug
            print(f"DEBUG: task detection agent: {state['nodes_to_visit']}") #debug
            
            state["visited_nodes"].append("task_detection")
            state["general_description"] = result_dict.get("general_description", "")
            state["course_description_keywords"].extend(result_dict.get("course_description_keywords", []))
            state["messages"].extend([
                HumanMessage(content=state["query"]).model_dump(),
                AIMessage(content=f"Nodes to visit: {', '.join(result_dict['nodes_to_visit'])}").model_dump()
            ])
        except Exception as e:
            state["error"] = f"Failed to detect task: {e}"
        
        return state