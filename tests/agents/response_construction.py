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
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that constructs responses based on course descriptions and SQL query results. Provide a concise and informative answer to the user's query."),
            ("user", "User Query: {query}\n\nCourse Description Results: {course_results}\n\nSQL Query Results: {sql_results}\n\nConstruct a response to the user's query based on this information.")
        ])

    def construct_response(self, state: AgentState) -> AgentState:

        print("DEBUG: Executing response contruction agent") #debug

        response = self.llm.invoke(
            self.prompt.format(
                query=state["query"],
                course_results=state.get("course_description_results", {}),
                sql_results=state.get("sql_results", {})
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