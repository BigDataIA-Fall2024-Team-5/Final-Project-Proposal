from tavily import TavilyClient

# Tavily API key
api_key = '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'
client = TavilyClient(api_key=api_key)

def ask_tavily(question):
    try:
        # Fetch results from Tavily
        response = client.search(
            query=question,
            include_domains=['northeastern.edu']
        )
        
        if 'results' in response and response['results']:
            # Sort results by score and limit to the top 3
            top_results = sorted(response['results'], key=lambda x: x['score'], reverse=True)[:3]
            
            # Format the response
            formatted_response = []
            for result in top_results:
                formatted_response.append({
                    'Title': result['title'],
                    'URL': result['url'],
                    'Snippet': result['content'],
                    'Score': result['score']
                })
            
            return formatted_response
        else:
            return "No results found."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    question = 'Could you tell me the steps to register for courses in nubanner?'
    top_responses = ask_tavily(question)
    print("Top 3 Results:")
    for i, res in enumerate(top_responses, start=1):
        print(f"\nResult {i}:")
        print(f"Title: {res['Title']}")
        print(f"URL: {res['URL']}")
        print(f"Snippet: {res['Snippet']}")
        print(f"Score: {res['Score']}")
