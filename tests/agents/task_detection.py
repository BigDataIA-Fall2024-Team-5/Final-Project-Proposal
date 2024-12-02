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
                "and routing them to the appropriate tools. Your responsibilities are:\n"
                "1. Classify queries into one of the following types:\n"
                "   - 'course_description': Queries focused on conceptual matches with courses (e.g., 'Suggest me a course with Python').\n"
                "   - 'sql_agent': Queries requiring precise data retrieval from a SQL database "
                "(e.g., 'What are the timings for INFO 7245?').\n"
                "   - 'course_description+sql_agent': Queries that combine conceptual matches with SQL queries "
                "(e.g., 'What courses on Python are available, and when can I take them?').\n"
                "   - 'response_construction': Queries that do not require further analysis (e.g., 'Summarize the results').\n"
                "2. Generate relevant keywords for 'course_description':\n"
                "   - Focus on detailed topics, related technologies, and domain-specific skills.\n"
                "   - Expand keywords to include synonyms, tools, and techniques used in the field.\n"
                "   - Examples:\n"
                "     - For 'ML', generate: ['Machine Learning', 'ML', 'Artificial Intelligence', 'AI', "
                "'Deep Learning', 'Neural Networks', 'Python', 'TensorFlow', 'Scikit-learn', 'Data Science'].\n"
                "     - For 'Cloud Computing', generate: ['Cloud Computing', 'AWS', 'Azure', 'GCP', 'Kubernetes', "
                "'Docker', 'Virtualization', 'Infrastructure-as-a-Service (IaaS)'].\n"
                "3. Output a JSON with:\n"
                "   - 'type': The query type ('course_description', 'sql_agent', 'course_description+sql_agent', or 'response_construction').\n"
                "   - 'course_description_keywords': List of keywords relevant to course descriptions (if applicable).\n"
                "   - 'explanation': Brief explanation of the classification."
            ),
            ("user", "{query}"),
        ])

    def detect_task(self, state: AgentState) -> AgentState:
        input_message = {"query": state["query"]}
        response = self.prompt | self.llm
        try:
            result = response.invoke(input_message)
            result_dict = json.loads(result.content)
            if not all(key in result_dict for key in ["type", "explanation"]):
                raise ValueError("Incomplete response from LLM.")
            
            state["query_type"] = result_dict["type"]
            state["course_description_keywords"] = result_dict.get("course_description_keywords", [])
            state["visited_nodes"] = state.get("visited_nodes", []) + ["task_detection"]
            state["messages"].extend([
                HumanMessage(content=state["query"]).model_dump(),
                AIMessage(content=f"Detected query type: {result_dict['type']}").model_dump()
            ])
        except Exception as e:
            state["error"] = f"Failed to detect task: {e}"
        
        return state


