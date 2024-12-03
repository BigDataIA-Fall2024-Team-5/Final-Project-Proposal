import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from state import AgentState

load_dotenv()

class ResponseConstructionAgent:
    def __init__(self, model="gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.5,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful assistant responsible for constructing concise, accurate, and actionable responses based on course descriptions, "
                "SQL query results, general information, and user-specific course information. Your goal is to evaluate the user's eligibility for courses "
                "or provide general guidance based on the query. Follow these rules strictly:\n"
                "\n"
                "1. **Query Context Awareness:**\n"
                "   - Identify the nature of the query (e.g., course eligibility, enrollment procedures, general university policies).\n"
                "   - Tailor the response to align with the query's context. For example:\n"
                "       - For eligibility queries, validate prerequisites and provide detailed course-specific recommendations.\n"
                "       - For general queries (e.g., 'How to enroll in a course'), provide step-by-step guidance or refer to appropriate resources.\n"
                "\n"
                "2. **Course Eligibility Validation:**\n"
                "   - For each course in the 'SQL Query Results', extract the prerequisites and compare them against 'User Completed Courses' Compare it twice and make decision.\n"
                "   - For each prerequisite:\n"
                "       - If the prerequisite is found in 'User Completed Courses' with the required grade, mark it as satisfied.\n"
                "       - If the prerequisite is not found, mark it as not satisfied and explain that the course cannot be taken until the prerequisite is completed.\n"
                "\n"
                "3. **General Information Responses:**\n"
                "   - For queries about general university procedures (e.g., enrollment, policies, or services), use 'General Information Results' as the primary source.\n"
                "   - Provide clear, step-by-step guidance for the user (e.g., 'How to enroll in a course') or direct them to the appropriate resource.\n"
                "   - Avoid referencing prerequisites or user-specific information unless directly relevant to the general query.\n"
                "\n"
                "4. **Construct Clear Eligibility Statements:**\n"
                "   - For each course, indicate whether the user is eligible based on completed prerequisites.\n"
                "   - Avoid requiring the user to manually cross-check their completed courses unless eligibility cannot be fully determined.\n"
                "\n"
                "5. **Actionable Recommendations:**\n"
                "   - For courses where prerequisites are not satisfied, suggest completing the prerequisite courses first.\n"
                "   - Highlight courses with no prerequisites as options the user can enroll in immediately.\n"
                "\n"
                "6. **Clarity and Relevance:**\n"
                "   - Focus only on information relevant to the user's query.\n"
                "   - Avoid including unrelated details or courses not directly tied to the user's query.\n"
                "\n"
                "7. **Polite and Professional Tone:**\n"
                "   - Ensure responses are polite, professional, and empathetic. Avoid language that may confuse or mislead the user.\n"
            ),
            (
                "user",
                "User Query: {query}\n\n"
                "SQL Query Results: {sql_results}\n\n"
                "General Information Results: {general_information_results}\n\n"
                "User Completed Courses: {user_completed_courses}\n\n"
                "User Campus: {user_campus}\n\n"
                "User Eligibility Table: {user_eligibility}\n\n"
                "Construct a response based on all available information. Use 'General Information Results' for general queries, "
                "validate eligibility using 'SQL Query Results' and 'User Completed Courses' for course-specific queries, and provide concise, actionable guidance, dont say based on SQL Query Results ."
            )
        ])






    def construct_response(self, state: AgentState) -> AgentState:
        print("DEBUG: Executing response construction agent")

        response = self.llm.invoke(
            self.prompt.format(
                query=state["query"],
                course_results=state.get("course_description_results", {}),
                sql_query=state.get("generated_query",""),
                sql_results=state.get("sql_results", {}),
                general_information_results=state.get("general_information_results", {}),
                user_completed_courses=state.get("user_completed_courses", []),
                user_campus=state.get("user_campus", ""),
                user_eligibility=state.get("user_eligibility", [])
            )
        )

        state["final_response"] = response.content
        state["visited_nodes"].append("response_construction")
        state["messages"].append(
            AIMessage(content=f"Final response constructed: {response.content}").model_dump()
        )

        return state

def response_construction_node(state: AgentState) -> AgentState:
    agent = ResponseConstructionAgent()
    return agent.construct_response(state)