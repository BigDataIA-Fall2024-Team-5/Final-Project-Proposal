import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from state import AgentState

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
                "   - 'sql_agent': For queries requiring precise data retrieval from a SQL database "
                "(e.g., 'What are the timings for INFO 7245?').\n"
                "   - Both 'course_description' and 'sql_agent': For queries that combine conceptual matches with SQL queries "
                "(e.g., 'What courses on Python are available, and when can I take them?').\n"
                "   - 'general_information': Queries that require information from general resources "
                "(e.g., 'What are the on-campus job opportunities').\n"
                "   - 'response_construction': Queries that do not require further analysis (e.g., 'Summarize the results').\n"
                "2. Generate relevant keywords for course description searches:\n"
                "   - Focus on detailed topics, related technologies, and domain-specific skills.\n"
                "   - Expand keywords to include synonyms, tools, and techniques used in the field.\n"
                "   - Examples:\n"
                "     - For 'ML', generate: ['Machine Learning', 'ML', 'Artificial Intelligence', 'AI', "
                "'Deep Learning', 'Neural Networks', 'Python', 'TensorFlow', 'Scikit-learn', 'Data Science'].\n"
                "     - For 'Cloud Computing', generate: ['Cloud Computing', 'AWS', 'Azure', 'GCP', 'Kubernetes', "
                "'Docker', 'Virtualization', 'Infrastructure-as-a-Service (IaaS)'].\n"
                "3. Output a JSON with:\n"
                "   - 'nodes_to_visit': List of nodes to visit ('course_description', 'general_information', 'sql_agent', or both).\n"
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