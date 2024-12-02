import os
import json
from pinecone import Pinecone as PineconeClient
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

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
            print(f"Connecting to Pinecone index: {self.pinecone_index_name}")
            self.pinecone_index = pc.Index(self.pinecone_index_name)
            # Check if the index is accessible
            info = self.pinecone_index.describe_index_stats()
            print(f"Connection established. Index stats: {json.dumps(info.to_dict(), indent=4)}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Pinecone index '{self.pinecone_index_name}': {e}")

    def generate_embedding(self, query):
        try:
            print(f"Generating embeddings for query: {query}")
            embedding = embedding_client.embed_query(query)
            print(f"Generated embedding: {embedding[:10]}...")  # Display only first 10 dimensions for brevity
            return embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings for query '{query}': {e}")

    def search(self, query):
        if not query:
            return {"error": "Query text is missing."}
        try:
            # Generate embeddings for the query
            query_embedding = self.generate_embedding(query)

            # Perform search on Pinecone
            print(f"Searching Pinecone index with embedding...")
            search_results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True
            )
            print(f"Pinecone response: {json.dumps(search_results.to_dict(), indent=4)}")

            # Parse matches
            matches = search_results.to_dict().get("matches", [])
            results = [
                {
                    "text": match["metadata"].get("text", "No information available"),
                    "score": match.get("score", 0)
                }
                for match in matches
            ]
            return results
        except Exception as e:
            return {"error": f"Search failed: {e}"}

# Test the agent with a predefined query
def main():
    # Initialize the agent
    agent = GeneralInformationAgent()

    # Predefined query for testing
    query = "tell me about LGBTQA"

    # Perform the search
    print(f"Query: {query}")
    results = agent.search(query)

    # Print the results
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        print("Search Results:")
        for result in results:
            print(f"Score: {result['score']}")
            print(f"Text: {result['text']}\n")

if __name__ == "__main__":
    main()
