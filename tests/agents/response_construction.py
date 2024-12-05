import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from state import AgentState

load_dotenv()

class ResponseConstructionAgent:
    def __init__(self, model="gpt-4"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.5,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the final response agent and helpful assistant responsible for constructing concise, accurate, and actionable responses based on availble infomation, "
                "SQL query results, general information, and user-specific course information. Your goal is answer the query with available details (like evaluating the user's eligibility for courses "
                "or provide general guidance based on the query. Follow these rules strictly:\n"
                "\n"
                "1. **Query Context Awareness:**\n"
                "   - Identify the nature of the query (e.g., course eligibility, enrollment procedures, general university policies, course details).\n"
                "   - Tailor the response to align with the query's context. For example:\n"
                "       - For eligibility queries, validate prerequisites and provide detailed course-specific recommendations.\n"
                "       - For general queries (e.g., 'How to enroll in a course'), provide step-by-step guidance or refer to appropriate resources.\n"
                "\n"
                "2. **Course Eligibility Validation:**\n"
                "   - Use 'SQL Query Results' and 'user_course_details' to determine eligibility for courses:\n"
                "       - For each course in 'SQL Query Results', extract the prerequisites.\n"
                "       - Compare prerequisites against 'user_course_details', specifically completed courses and grades.\n"
                "       - Check whether the course is already completed, in progress, or not started.\n"
                "       - Evaluate progress in related program categories (e.g., core requirements, electives, subject areas) when applicable.\n"
                "\n"
                "3. **General Information Responses:**\n"
                "   - For queries about general university procedures (e.g., enrollment, policies, or services), use 'General Information Results' as the primary source.\n"
                "   - Provide clear, step-by-step guidance for the user (e.g., 'How to enroll in a course') or direct them to the appropriate resource.\n"
                "   - Avoid referencing specific courses, prerequisites, or program categories unless directly relevant to the general query.\n"
                "\n"
                "4. **Dynamic Adaptation to User Data:**\n"
                "   - Interpret 'user_course_details' dynamically based on user-specific data. Examples include:\n"
                "       - Identifying completed courses and their corresponding categories (e.g., core requirements, electives).\n"
                "       - Checking credits completed in subject areas (e.g., INFO) and elective requirements.\n"
                "       - Recognizing in-progress courses and ensuring these do not satisfy prerequisites yet.\n"
                "       - Handling exceptions or additional program rules (e.g., certain courses counting as electives).\n"
                "\n"
                "5. **Construct Clear Eligibility Statements:**\n"
                "   - For each course, indicate whether the user is eligible based on prerequisites and program progress.\n"
                "   - Avoid requiring the user to manually cross-check their completed courses unless eligibility cannot be fully determined.\n"
                "\n"
                "6. **Actionable Recommendations:**\n"
                "   - For courses where prerequisites are not satisfied, suggest completing the prerequisite courses first.\n"
                "   - Highlight courses with no prerequisites or courses that fit into remaining program requirements as options the user can enroll in immediately.\n"
                "\n"
                "7. **Clarity and Relevance:**\n"
                "   - Focus only on information relevant to the user's query.\n"
                "   - Avoid including unrelated details or courses not directly tied to the user's query.\n"
                "\n"
                "8. **Polite and Professional Tone:**\n"
                "   - Ensure responses are polite, professional, and empathetic. Avoid language that may confuse or mislead the user.\n"
            ),
            (
                "user",
                "User Query: {query}\n\n"
                "SQL Query (Dont mention it to user): {sql_query}\n\n"
                "SQL Query Agent Results: {sql_results}\n\n"
                "General Information Results: {general_information_results}\n\n"
                "User Details:\n"
                "  - GPA: {user_gpa}\n"
                "  - Completed Credits: {user_completed_credits}\n"
                "  - Credits Left: {user_credits_left}\n"
                "  - Program Name: {user_program_name}\n"
                "  - Campus: {user_campus}\n"
                "  - College: {user_college}\n\n"
                "User Course Details: {user_course_details}\n\n (Has details about user enrolled program with all core courses(even if not completed),core option,elective,subject area)"
                "Course Description Results: {course_description_results}\n\n"
                "Construct a response based on all available information and which is relavent to user query. Use 'General Information Results' for general queries, "
                "When a question on a specific program/core/elective other than the users program is asked check sql query and result. if sql result is empty then answer accordingly (mostly no for specified filter from sql query) "
                "validate eligibility using 'SQL Query Results' and 'user_course_details' for course-specific queries, and provide concise, actionable guidance without referencing the raw SQL Query Results."
            )
        ])

    def construct_response(self, state: AgentState) -> AgentState:
        print("DEBUG: Executing response construction agent")

         # Extract user details or set defaults
        user_details = state.get("user_details", {}) or {}
        user_gpa = user_details.get("gpa", "N/A")
        user_completed_credits = user_details.get("completed_credits", "N/A")
        user_credits_left = user_details.get("credits_left", "N/A")
        user_program_name = user_details.get("program_name", "N/A")
        user_campus = user_details.get("campus", "N/A")
        user_college = user_details.get("college", "N/A")

        response = self.llm.invoke(
            self.prompt.format(
                query=state["query"],
                user_gpa=user_gpa,
                user_completed_credits=user_completed_credits,
                user_credits_left=user_credits_left,
                user_program_name=user_program_name,
                user_campus=user_campus,
                user_college=user_college,
                sql_query=state.get("sql_query", {}),
                sql_results=state.get("sql_results", {}),
                general_information_results=state.get("general_information_results", {}),
                user_course_details=state.get("user_course_details", []),
                course_description_results=state.get("course_description_results",[])
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