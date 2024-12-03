import os
import snowflake.connector
from dotenv import load_dotenv
from state import AgentState, create_agent_state

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

    def get_user_completed_courses(self, user_id):
        query = """
        SELECT course_code, grade
        FROM USER_COURSES
        WHERE user_id = %s
        """
        return self.db_query(query, (user_id,))

    def get_user_campus(self, user_id):
        query = """
        SELECT campus
        FROM USER_PROFILE
        WHERE user_id = %s
        """
        return self.db_query(query, (user_id,))

    def get_user_eligibility(self, user_id):
        query = """
        SELECT CODE, REASON 
        FROM USER_ELIGIBILITY
        WHERE user_id = %s
        """
        return self.db_query(query, (user_id,))

    def process(self, state: AgentState) -> AgentState:
        user_id = state["user_id"]
        
          
        state["user_completed_courses"] = self.get_user_completed_courses(user_id)
        state["user_campus"] = self.get_user_campus(user_id)
        state["user_eligibility"] = self.get_user_eligibility(user_id)

        state["visited_nodes"].append("user_course_agent")
        state["messages"].append({
            "role": "assistant",
            "content": "User course information retrieved."
        })

        return state

def user_course_agent_node(state: AgentState) -> AgentState:
    agent = UserCourseAgent()
    return agent.process(state)

# Test function
def test_user_course_agent():
    test_query = "What courses am I eligible for in data?"
    test_user_id = 1
    state = create_agent_state(test_query, test_user_id)
    state["course_description_results"] = [
        {"course_code": "INFO 7250", "course_name": "Engineering of Big-Data Systems"},
        {"course_code": "INFO 7255", "course_name": "Advanced Big-Data Applications and Indexing Techniques"}
    ]
    
    agent = UserCourseAgent()
    final_state = agent.process(state)

    print("\n--- User Course Agent Test Results ---")
    print(f"Query: {test_query}")
    print(f"User ID: {test_user_id}")
    print(f"Course Prerequisites: {final_state.get('course_prerequisites', 'N/A')}")
    print(f"User Completed Courses: {final_state.get('user_completed_courses', 'N/A')}")
    print(f"User Campus: {final_state.get('user_campus', 'N/A')}")
    print(f"User Eligibility: {final_state.get('user_eligibility', 'N/A')}")
    print(f"Visited Nodes: {final_state.get('visited_nodes', [])}")

if __name__ == "__main__":
    test_user_course_agent()