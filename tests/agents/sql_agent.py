import os
import snowflake.connector
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState, create_agent_state

load_dotenv()

class SQLAgent:
    def __init__(self, model="gpt-4"):
        self.conn = self.snowflake_setup()
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert SQL query generator. Given a user query, database schema, and relevant course codes, generate a SQL query to answer the user's question. Note that in the CLASSES table, terms are represented as 'Spring YYYY Semester' or 'Fall YYYY Semester', where YYYY is the year."),
            ("user", "User Query: {query}\n\nDatabase Schema:\n{schema}\n\nRelevant Course Codes: {course_codes}\n\nGenerate a SQL query to answer the user's question, focusing on the relevant course codes if provided. Remember to use the correct term format (e.g., 'Fall 2024 Semester') when querying the CLASSES table."),
        ])
        self.tables = [
            "PROGRAM_REQUIREMENTS", "CORE_REQUIREMENTS", "CORE_OPTIONS_REQUIREMENTS",
            "SUBJECT_AREAS", "USER_COURSES", "USER_ELIGIBILITY", "ELECTIVE_REQUIREMENTS",
            "COURSE_CATALOG", "CLASSES"
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
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            return {"error": f"Query execution failed: {e}"}
        finally:
            cursor.close()

    def generate_query(self, user_query: str, schema: str, course_codes: list) -> str:
        response = self.llm.invoke(self.prompt.format(
            query=user_query,
            schema=schema,
            course_codes=", ".join(course_codes)
        ))
        return response.content.strip()

    def process(self, state: AgentState) -> AgentState:
        
        print("DEBUG: Executing sql agent") #debug
        
        schema = self.get_schema()
        course_codes = []
        if state.get("course_description_results"):
            course_codes = [result["course_code"] for result in state["course_description_results"] if result["course_code"] != "Unknown"]
        
        generated_query = self.generate_query(state["query"], schema, course_codes)

        if not generated_query:
            state["sql_results"] = {"error": "No valid query generated to execute."}
        else:
            state["generated_query"] = generated_query
            state["sql_results"] = self.db_query(generated_query)

        state["visited_nodes"].append("sql_agent")
        state["messages"].append({
            "role": "assistant",
            "content": f"SQL query execution completed. Results: {state['sql_results']}"
        })

        return state

def sql_agent_node(state: AgentState) -> AgentState:
    agent = SQLAgent()
    return agent.process(state)




def test_sql_agent(query: str):
    state = create_agent_state(query)
    state["course_description_results"] = [
        {"course_code": "INFO 7250", "course_name": "Engineering of Big-Data Systems"},
        {"course_code": "INFO 7255", "course_name": "Advanced Big-Data Applications and Indexing Techniques"}
    ]
    agent = SQLAgent()
    final_state = agent.process(state)

    print("\n--- SQL Agent Test Results ---")
    print(f"Query: {query}")
    print(f"Generated SQL Query: {final_state.get('generated_query', 'N/A')}")
    print(f"SQL Results: {final_state.get('sql_results', 'N/A')}")
    print(f"Visited Nodes: {final_state.get('visited_nodes', [])}")

if __name__ == "__main__":
    test_query = "What courses on BigData Analytics are available in the Spring 2025 semester?"
    test_sql_agent(test_query)