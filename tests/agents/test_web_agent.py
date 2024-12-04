from serpapi import GoogleSearch
import os
from dotenv import load_dotenv
from state import AgentState
from langchain_core.messages import AIMessage
from web_agent import WebAgent  # Import the WebAgent class from web_agent.py
def test_web_agent():
    # Test cases focusing on different types of university information
    test_queries = [
        "Tell me about housing options",
        "What dining services are available",
        "Student organizations",
    ]
    
    agent = WebAgent()
    
    for query in test_queries:
        print(f"\nTesting query: {query}")
        print("="*50)
        
        # Create test state
        state = {
            "query": query,
            "web_search_results": [],
            "visited_nodes": [],
            "messages": []
        }
        
        try:
            result_state = agent.search(state)
            results = result_state.get("web_search_results", [])
            
            if isinstance(results, dict) and "error" in results:
                print(f"Error: {results['error']}")
            else:
                print(f"Found {len(results)} results\n")
                
                for i, result in enumerate(results, 1):
                    print(f"Result {i}:")
                    print("Summary:")
                    print(result['summary'])
                    print(f"\nSource: {result['source']}")
                    print("-" * 40)
                    
        except Exception as e:
            print(f"Test failed: {str(e)}")
            print(f"Error type: {type(e)}")
            print("-" * 40)

if __name__ == "__main__":
    print("Starting Web Agent Tests...")
    print("=" * 50)
    test_web_agent()