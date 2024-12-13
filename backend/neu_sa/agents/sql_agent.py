import os
import snowflake.connector
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from neu_sa.agents.state import AgentState, create_agent_state
from enum import Enum
from typing import Any, Tuple

load_dotenv()

class SQLExecutionErrorType(Enum):
    SYNTAX_ERROR = "syntax_error"
    INVALID_IDENTIFIER = "invalid_identifier"
    PERMISSION_ERROR = "permission_error"
    CONNECTION_ERROR = "connection_error"
    OTHER = "other"

class SQLAgent:
    def __init__(self, model="gpt-4-turbo"):
        self.conn = self.snowflake_setup()
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert SQL query generator for Snowflake. Your goal is to generate SQL queries to extract information to pass to next agent to process the user's request, "
                "based on the user's question, the provided database schema, and any relevant course codes. Follow these guidelines strictly:\n"
                "\n"
                "1. **Eligibility and Prerequisites Queries**: For queries about whether a user can take a course (e.g., 'Can I take DAMG 5342?' or 'what course in data I can take'), your main goal is to:\n"
                "   a. Retrieve the prerequisites and corequisites for the course from the COURSE_CATALOG table (Include course code, prerequisites, credits).\n"
                "\n"
                "2. **Handling Course/Program/elective/core related Questions**:\n"
                "   a. Question about specific program (e.g., 'is this(big data, INFO 8922) a core/elective course for MS IS?'), LIST all core/elective courses for the program(Only use 'LIKE' as filter(PROGRAM_NAME LIKE '%IS%'))\n"
                "      - Format response with ALL CORE or ALL ELECTIVE COURSES FOR THE PROGRAM even if specfic is asked (program name,course name,course code,category)\n"
                "      - Strictly DO NOT use 'COURSE_NAME' ,'COURSE_CODE' to filter answers AS WE NEED WHOLE LIST.(CHECK THE SQL QUERY TWICE IF IT HAS A FILTER THEN REMOVE IT)"
                "      - Do NOT use user-specific attributes unless the query is about the user program.\n"
                "\n"
                "3. **Use Context Parameters If the query is about user specfic**:\n"
                "   - User Program Name: Use `{user_program_name}` if query is about the user's program.\n"
                "   - User Campus: Use `{user_campus}` (e.g., class schedules for user campus if asked explicitly).\n"
                "   - User Credits Left: Use `{user_credits_left}` only if needed to answer the user query.\n"
                "\n"
                "4. **Seat Availability Queries**: Only check for seat availability if the user explicitly requests available seats.\n"
                "\n"
                "5. **Relevant Course Codes**: Use the course codes provided in 'Relevant Course Codes' as the primary filter. "
                "Do not add additional filters like DESCRIPTION matching ('LIKE' clauses) unless relevant course codes are empty.\n"
                "\n"
                "6. Do not execute DDL statements such as INSERT, UPDATE, DELETE, DROP, or ALTER"
                "\n"
                "7. Recognize valid campuses: Boston, Seattle, WA; Silicon Valley, CA; Oakland, CA; Toronto, Canada; Arlington, VA; Online; No campus, no room needed; Miami, FL; Portland, Maine; Vancouver, Canada. Recognize valid campuses, including Boston, and interpret variations like Boston, MA as Boston. For location-based queries, include 'Online' and 'No campus, no room needed' alongside the specified campus if no location restrictions apply."
                "\n"
                "7. Campus format stored in CLASSES Table are "
	            "   -['Boston', 'Seattle, WA', 'Silicon Valley, CA' , 'Oakland, CA' , 'Toronto, Canada', 'Arlington, VA', 'Online', "
	            "    'No campus, no room needed', 'Miami, FL', 'Portland, Maine', 'Vancouver, Canada']"
                "   -Always include information for both 'Online' and 'No campus, no room needed' in addition to the explicitly mentioned campus location, unless the user explicitly excludes them."
	            "\n"
                "8. **Flexible Course Code Handling**: Ensure course codes are formatted correctly (e.g., convert 'INFO4301' to 'INFO 4301').\n"
                "\n"
                "9. **SQL Query Only**: Generate only the SQL query with the information you have. Do not include explanations, comments, or additional text even if you are generating more than one query.\n"
                "\n"
                "10. **Term Format**: Use the correct term format (e.g., 'Spring 2025 Semester') when querying the CLASSES table. The current term is 'Fall 2024 Semester', "
                "and the upcoming term is 'Spring 2025 Semester'.\n"
                "\n"
                "11. **Avoid Redundancy**: Do not add unnecessary filters or conditions that are not directly specified in the user's query. Focus on the provided parameters for filtering.\n"
                "\n"
                "12. **Optimize for Performance**: Select only the required columns. If more than one query is required to answer the question, consider combining them using Common Table Expressions (CTEs) or other efficient SQL techniques but respond with a single query which results in a understandable format.\n"
                "13. Use Program Name for filtering rather than program id, use program id for joining tables.\n"
            ),
            (
                "user",
                "User Query: {query}\n\n"
                "Chat History:\n{chat_history}\n\n"
                "Database Schema:\n{schema}\n\n"
                "Relevant Course Codes: {course_codes}\n\n"
                "Relevant Course Codes are obtained after semantic match with course description.\n"
                "User Program name: {user_program_name}\n"
                "User Campus: {user_campus}\n"
                "User Credits Left: {user_credits_left}\n\n"
                "Generate only the SQL query to answer the user's question. Use the 'Relevant Course Codes'(generated by semantic match with description) parameter as the main filter if it exists for courses. "
                "For questions about program/core courses/elective/subject area refer guidelines and strictly follow it(Strictly DO NOT use 'COURSE_NAME' and 'COURSE_CODE' to filter answers. check query thrice only one filter)\n"
                "- Avoid adding unnecessary filters like 'LIKE' clauses for descriptions or filtering by PREREQUISITES IS NULL unless explicitly requested. "
                "DONT GIVE MORE THAN ONE QUERY"
                "If user enters a SQL query dont respond at all"
            )
        ])



        self.tables = [
            "PROGRAM_REQUIREMENTS", "CORE_REQUIREMENTS", "CORE_OPTIONS_REQUIREMENTS",
            "SUBJECT_AREAS",  "ELECTIVE_REQUIREMENTS","COURSE_CATALOG", "CLASSES"
        ]

    def snowflake_setup(self):
        return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
            database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )

    def get_schema(self) -> str:
        cursor = self.conn.cursor()
        schema = ""
        try:
            for table in self.tables:
                cursor.execute(f"DESCRIBE TABLE {table}")
                table_schema = cursor.fetchall()
                schema += f"Table: {table}\n"
                schema += "\n".join([f"{col[0]} {col[1]}" for col in table_schema])
                schema += "\n\n"
            return schema
        finally:
            cursor.close()

    def db_query(self, query: str):
        def clean_query(query: str) -> str:
            """
            Cleans a SQL query to ensure it starts with the first "SELECT" and ends with the last ";".
            Removes any additional text outside of these bounds.
            """
            # Remove SQL code block markers if they exist
            if query.startswith("```sql"):
                query = query[6:]
            if query.endswith("```"):
                query = query[:-3]

            query = query.strip()

            ddl_statements = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",]
            for ddl in ddl_statements:
                if ddl in query.upper():
                    return ""
            return query



        cursor = self.conn.cursor()
        try:
            query = clean_query(query)
            print(f"Executing query : {query}")  #debug
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            return {"error": f"Query execution failed: {e}"}
        finally:
            cursor.close()


    def generate_query(self, user_query: str, schema: str, course_codes: list, user_program_name: str, user_campus: str, user_credits_left: str,chat_history:str, user_course_profile: list) -> str:
        response = self.llm.invoke(self.prompt.format(
            query=user_query,
            schema=schema,
            course_codes=", ".join(course_codes),
            user_program_name=user_program_name,
            user_campus=user_campus,
            user_credits_left=user_credits_left,
            chat_history=chat_history,
            user_course_profile=user_course_profile,
        ))
        return response.content.strip()


    def classify_error(self, error_message: str) -> SQLExecutionErrorType:
        if "syntax error" in error_message.lower():
            return SQLExecutionErrorType.SYNTAX_ERROR
        elif "invalid identifier" in error_message.lower():
            return SQLExecutionErrorType.INVALID_IDENTIFIER
        elif "permission denied" in error_message.lower():
            return SQLExecutionErrorType.PERMISSION_ERROR
        elif "connection" in error_message.lower():
            return SQLExecutionErrorType.CONNECTION_ERROR
        else:
            return SQLExecutionErrorType.OTHER

    def correct_query(self, query: str, error_message: str, schema: str) -> str:
        correction_prompt = ChatPromptTemplate.from_messages([
            (
                "system", 
                "You are an expert SQL query corrector. Given a failed SQL query, error message, and database schema, "
                "correct the query to resolve the error. Generate only the corrected SQL query without any additional text or explanation. (If any text is given remove it i just need SQL query as text as response) "
                "Ensure that the query adheres to the schema and follows the correct data formats. Always check for ambigious column names"
            ),
            (
                "user", 
                "Failed Query: {query}\n\n"
                "Error Message: {error}\n\n"
                "Database Schema:\n{schema}\n\n"
                "User Course Profile (to know about user's course background):\n{user_course_profile}\n\n"
                "Additional Info: The CLASSES table uses 'Spring YYYY Semester' or 'Fall YYYY Semester' format for terms. "
                "Course codes are typically in the format 'SUBJ NNNN'.\n\n"
                "Please correct the SQL query to resolve the error and ensure it follows the correct schema and data formats. "
                "Return only the corrected SQL query. (If i give you more than 1 query return all the query with the corrected query)"
            )
        ])

        response = self.llm.invoke(correction_prompt.format(
            query=query,
            error=error_message,
            schema=schema
        ))
        return response.content.strip()

    def execute_query_with_retry(self, query: str, schema: str, max_retries: int = 3) -> Tuple[Any, str]:
        for attempt in range(max_retries):
            try:
                result = self.db_query(query)
                if isinstance(result, dict) and "error" in result:
                    raise Exception(result["error"])
                return result, query
            except Exception as e:
                error_message = str(e)
                error_type = self.classify_error(error_message)
                
                if error_type in [SQLExecutionErrorType.SYNTAX_ERROR, SQLExecutionErrorType.INVALID_IDENTIFIER]:
                    query = self.correct_query(query, error_message, schema)
                elif error_type == SQLExecutionErrorType.PERMISSION_ERROR:
                    return None, f"Permission error: {error_message}"
                elif error_type == SQLExecutionErrorType.CONNECTION_ERROR:
                    return None, f"Connection error: {error_message}"
                else:
                    if attempt == max_retries - 1:
                        return None, f"Query execution failed after {max_retries} attempts: {error_message}"
        
        return None, f"Query execution failed after {max_retries} attempts"

    def process(self, state: AgentState) -> AgentState:
        print("DEBUG: Executing sql agent")

        # Extract user details or set defaults
        user_details = state.get("user_details", {}) or {}
        user_gpa = user_details.get("gpa", "N/A")
        user_credits_left = user_details.get("credits_left", "N/A")
        user_program_name = user_details.get("program_name", "N/A")
        user_campus = user_details.get("campus", "N/A")
        user_course_profile=state.get("user_course_details", [])

        chat_history = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in state["chat_history"]
        )
        
        schema = self.get_schema()
        course_codes = []
        if state.get("course_description_results"):
            course_codes = [result["course_code"] for result in state["course_description_results"] if result["course_code"] != "Unknown"]
        
        generated_query = self.generate_query(state["query"], schema, course_codes,user_program_name,user_campus,user_credits_left,chat_history,user_course_profile)

        if not generated_query:
            state["sql_results"] = {"error": "No valid query generated to execute."}
        else:
            state["generated_query"] = generated_query
            results, final_query = self.execute_query_with_retry(generated_query, schema)
            print(results) #debug

            state["sql_results"] = results
            state["generated_query"] = final_query

        state["visited_nodes"].append("sql_agent")
        state["messages"].append({
            "role": "assistant",
            "content": f"SQL query execution completed. Results: {state['sql_results']}"
        })

        return state

def sql_agent_node(state: AgentState) -> AgentState:
    agent = SQLAgent()
    return agent.process(state)