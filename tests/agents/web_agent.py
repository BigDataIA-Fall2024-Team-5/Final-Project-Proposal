from serpapi import GoogleSearch
import os
from dotenv import load_dotenv
from state import AgentState
from langchain_core.messages import AIMessage

class WebAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('SERPAPI_API_KEY')
        
    def search(self, state: AgentState) -> AgentState:
        print("DEBUG: Executing web search agent")
        
        query = state["query"]
        if not query:
            state["web_search_results"] = {
                "error": "No query provided for web search."
            }
            return state
            
        try:
            search = GoogleSearch({
                "q": f"Northeastern University {query}",
                "location": "Boston, Massachusetts",
                "hl": "en",
                "gl": "us",
                "google_domain": "google.com",
                "api_key": self.api_key,
                "num": 2  # Limit to top 2 results
            })
            
            results = search.get_dict()
            
            processed_results = []
            for result in results.get('organic_results', []):
                processed_results.append({
                    'summary': result.get('snippet', '')[:200],
                    'source': result.get('link', '')
                })
            
            state["web_search_results"] = processed_results
            state["visited_nodes"].append("web_search")
            state["messages"].append(
                AIMessage(content="Found relevant information from Northeastern sources").model_dump()
            )
            
        except Exception as e:
            state["web_search_results"] = {
                "error": f"Web search failed: {e}"
            }
            
        return state