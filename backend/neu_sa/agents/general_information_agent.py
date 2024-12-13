import os
from dotenv import load_dotenv
from pinecone import Pinecone as PineconeClient
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_core.messages import AIMessage
from tavily import TavilyClient
from neu_sa.agents.state import AgentState 

# Load environment variables
load_dotenv()

# Initialize Pinecone Client
pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize NVIDIA embedding client
embedding_client = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END"
)

# Initialize Tavily Client
tavily_api_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=tavily_api_key)


class GeneralInformationAgent:
    def __init__(self, pinecone_index_name="general-information-index"):
        self.pinecone_index_name = pinecone_index_name
        try:
            self.pinecone_index = pc.Index(self.pinecone_index_name)
            self.pinecone_index.describe_index_stats()  # Validate index connection
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Pinecone index '{self.pinecone_index_name}': {e}")

    def generate_embedding(self, query):
        try:
            return embedding_client.embed_query(query)
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings for query '{query}': {e}")

    def search_pinecone(self, query):
        try:
            query_embedding = self.generate_embedding(query)
            search_results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True
            )
            matches = search_results.to_dict().get("matches", [])
            results = [
                {
                    "text": match["metadata"].get("text", "No information available"),
                    "score": match.get("score", 0)
                }
                for match in matches
                if match["metadata"].get("text", "").strip()
            ]
            
            # Apply a relevance threshold
            threshold = 0.6
            if results and max(result["score"] for result in results) >= threshold:
                print("DEBUG: Pinecone results meet the threshold.")
                return results
            print("DEBUG: Pinecone results do not meet the threshold.")
            return []  # Fallback if no relevant results
        except Exception as e:
            raise RuntimeError(f"Pinecone search failed: {e}")

    def search_tavily(self, query):
        try:
            response = tavily_client.search(
                query=query,
                include_domains=["northeastern.edu"]  # Restrict search to Northeastern University's domain
            )
            if "results" in response and response["results"]:
                results = [
                    {
                        "title": result["title"],
                        "url": result["url"],
                        "snippet": result["content"],
                        "score": result.get("score", 0)
                    }
                    for result in sorted(response["results"], key=lambda x: x.get("score", 0), reverse=True)[:3]
                ]
            print("DEBUG: No relevant results from Tavily.")
            return []
        except Exception as e:
            raise RuntimeError(f"Tavily search failed: {e}")

    def search(self, state: AgentState) -> AgentState:
        # Retrieve the generalized description from the state
        query = state.get("general_description") or state.get("query")

        if not query:
            return {"error": "Query text is missing."}
        try:
            # Pinecone search
            print(f"General Information query : {query}") #debug
            pinecone_results = self.search_pinecone(query)
            if pinecone_results:
                print("DEBUG: Using Pinecone results.") #debug
                state["general_information_results"] = pinecone_results
                state["visited_nodes"].append("general_information_pinecone")
            else:
                # Fallback to Tavily
                print("DEBUG: Falling back to Tavily.")
                tavily_results = self.search_tavily(query)
                if tavily_results:
                    print("DEBUG: Using Tavily results.")
                    state["general_information_results"] = tavily_results
                    state["visited_nodes"].append("general_information_tavily")
                else:
                    print("DEBUG: No relevant results found from Tavily.")
                    state["general_information_results"] = []
                    state["visited_nodes"].append("general_information_no_results")

            # Add results and debug message
            state["messages"].append(
                AIMessage(content=f"General information search completed. Results: {state['general_information_results']}").model_dump()
            )

            return state
        except Exception as e:
            return {"error": f"Search failed: {e}"}
