import os
from pinecone import Pinecone as PineconeClient
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from neu_sa.agents.state import AgentState

load_dotenv()

# Initialize Pinecone Client
pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize NVIDIA embedding client
embedding_client = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END"
)

class CourseDescriptionAgent:
    def __init__(self, pinecone_index_name="course-catalog-index"):
        self.pinecone_index_name = pinecone_index_name
        try:
            self.pinecone_index = pc.Index(self.pinecone_index_name)
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Pinecone index '{self.pinecone_index_name}': {e}")

    def generate_embedding(self, query):
        try:
            return embedding_client.embed_query(query)
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings for query '{query}': {e}")

    def search(self, state: AgentState) -> AgentState:

        print("DEBUG: Executing course descriptions agent") #debug
        
        keywords = state["course_description_keywords"]
        if not keywords:
            state["course_description_results"] = {"error": "No keywords found for course description search."}
        else:
            query_text = " ".join(keywords)
            try:
                query_embedding = self.generate_embedding(query_text)
                search_results = self.pinecone_index.query(
                    vector=query_embedding,
                    top_k=5,
                    include_metadata=True
                )
                matches = search_results.get("matches", [])
                state["course_description_results"] = [
                    {
                        "course_code": match["metadata"].get("course_code", "Unknown"),
                        "course_name": match["metadata"].get("course_name", "Unknown"),
                        "description": match["metadata"].get("description", "No description available"),
                        "score": match.get("score", 0)
                    }
                    for match in matches
                ]
            except Exception as e:
                state["course_description_results"] = {"error": f"Search failed: {e}"}

        state["visited_nodes"].append("course_description")
        #state["visited_nodes"] = state.get("visited_nodes", []) + ["course_description"]
        state["messages"].append(AIMessage(content=f"Course description search completed. Results: {state['course_description_results']}").model_dump())
        #state["messages"] = state.get("messages", []) + [AIMessage(content=f"Course description search completed. Results: {state['course_description_results']}").model_dump()]
        return state
