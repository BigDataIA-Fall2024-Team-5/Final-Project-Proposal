import os
import json
from pinecone import Pinecone as PineconeClient
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
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

class GeneralInformationAgent:
    def __init__(self, pinecone_index_name="general-information-index"):
        self.pinecone_index_name = pinecone_index_name
        try:
            self.pinecone_index = pc.Index(self.pinecone_index_name)
            # Check if the index is accessible
            info = self.pinecone_index.describe_index_stats()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Pinecone index '{self.pinecone_index_name}': {e}")

    def generate_embedding(self, query):
        try:
            embedding = embedding_client.embed_query(query)
            return embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings for query '{query}': {e}")

    def search(self, state: AgentState) -> AgentState:

        print("DEBUG: Executing course descriptions agent") #debug
        
        query = state["query"]
        if not query:
            return {"error": "Query text is missing."}
        try:
            # Generate embeddings for the query
            query_embedding = self.generate_embedding(query)

            # Perform search on Pinecone
            search_results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True
            )

            # Parse matches
            matches = search_results.to_dict().get("matches", [])
            results = [
                {
                    "text": match["metadata"].get("text", "No information available"),
                    "score": match.get("score", 0)
                }
                for match in matches
                if match["metadata"].get("text", "").strip() not in ["", "."]
            ]
            state["general_information_results"] = results
            state["visited_nodes"].append("general_information")

            return state
        
        except Exception as e:
            return {"error": f"Search failed: {e}"}
