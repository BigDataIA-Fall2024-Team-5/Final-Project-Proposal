from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

db = SQLDatabase.from_uri("sqlite:///path/to/your/database.db")  # Update with your database path

@tool
def sql_query_tool(query: str) -> str:
    """Executes SQL queries and returns results."""
    result = db.run_no_throw(query)
    if not result:
        return "Error: Query failed. Please check your query."
    return result

class SQLAgent:
    def __init__(self, model="gpt-4"):
        self.model = ChatOpenAI(model=model, temperature=0)

    def generate_query(self, query, schema):
        """Generates SQL queries based on user input and schema."""
        prompt = f"You are a SQL expert. Based on this schema:\n{schema}\nWrite a query for: {query}"
        return self.model.invoke({"input": prompt})
