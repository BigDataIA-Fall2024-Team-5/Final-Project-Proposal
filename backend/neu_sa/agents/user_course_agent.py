import os
import snowflake.connector
from dotenv import load_dotenv
from neu_sa.agents.state import AgentState, create_agent_state

load_dotenv()

class UserCourseAgent:
    def __init__(self):
        self.conn = self.snowflake_setup()

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

    def db_query(self, query: str, params: tuple = None):
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            return {"error": f"Query execution failed: {e}"}
        finally:
            cursor.close()

    def get_user_details(self, user_id):
        query = """
        SELECT 
            UP.USER_ID,
            UP.USERNAME,
            UP.GPA,
            UP.COMPLETED_CREDITS,
            PR.MAX_CREDIT_HOURS - UP.COMPLETED_CREDITS AS CREDITS_LEFT,
            UP.PROGRAM_NAME,
            UP.CAMPUS,
            UP.COLLEGE,
            UP.PROGRAM_ID
        FROM 
            USER_PROFILE UP
        INNER JOIN 
            PROGRAM_REQUIREMENTS PR
        ON 
            UP.PROGRAM_ID = PR.PROGRAM_ID
        WHERE 
            UP.USER_ID = %s
        """
        return self.db_query(query, (user_id,))

    def get_user_eligibility(self, user_id):
        query = """
        SELECT COURSE_OR_REQUIREMENT, DETAILS 
        FROM USER_ELIGIBILITY
        WHERE user_id = %s
        """
        return self.db_query(query, (user_id,))

    def process(self, state: AgentState) -> AgentState:
        user_id = state["user_id"]
        
        # Fetch user details and eligibility
        user_details = self.get_user_details(user_id)
        eligibility_details = self.get_user_eligibility(user_id)

        # Assuming one user record; store details as a dictionary in state
        if user_details and isinstance(user_details, list) and len(user_details) > 0:
            user_details = user_details[0]  # Fetch first result
            state["user_details"] = {
                "user_id": user_details[0],
                "username": user_details[1],
                "gpa": user_details[2],
                "completed_credits": user_details[3],
                "credits_left": user_details[4],
                "program_name": user_details[5],
                "campus": user_details[6],
                "college": user_details[7],
                "program_id": user_details[8],
            }

        # Store eligibility details in state
        state["user_course_details"] = eligibility_details

        state["visited_nodes"].append("user_course_agent")
        state["messages"].append({
            "role": "assistant",
            "content": "User course information retrieved and stored as a dictionary."
        })

        return state
