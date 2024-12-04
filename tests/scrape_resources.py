import requests
from bs4 import BeautifulSoup
import re
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

# Get API keys from environment variables
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

def scrape_resources():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/university-graduate-resources/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unnecessary elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Find the content area
        content = soup.find('div', {'class': ['content', 'content-area', 'main-content']})
        if not content:
            content = soup.find('main') or soup.find('article')
        
        resources_text = []
        
        if content:
            # Find all list items
            list_items = content.find_all('li')
            
            print("\nRaw Data before chunking and indexing:")
            print("="*80)
            
            for li in list_items:
                resource_text = ""
                
                # Get title from first link
                links = li.find_all('a')
                if links:
                    resource_text += f"Title: {links[0].text.strip()}\n"
                
                # Get description
                text_content = li.get_text(separator=' ', strip=True)
                for link in links:
                    text_content = text_content.replace(link.text.strip(), '')
                if text_content.strip():
                    resource_text += f"Description: {text_content.strip()}\n"
                
                # Get links
                if links:
                    resource_text += "Links:\n"
                    for link in links:
                        if href := link.get('href'):
                            resource_text += f"- {link.text.strip()}: {href}\n"
                
                # Get phone numbers
                phone_numbers = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text_content)
                if phone_numbers:
                    resource_text += f"Phone Numbers: {', '.join(phone_numbers)}\n"
                
                if resource_text:
                    print(resource_text)
                    print("-"*80)
                    resources_text.append(resource_text)
        
        # Save raw text
        with open('graduate_resources.txt', 'w', encoding='utf-8') as f:
            for resource in resources_text:
                f.write(resource + "\n---\n")
        
        print(f"\nSuccessfully scraped {len(resources_text)} resources")
        return resources_text
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
def chunk_and_index_resources(resources_text):
    try:
        # Initialize NVIDIA embeddings
        embeddings_client = NVIDIAEmbeddings(
            model="nvidia/nv-embedqa-e5-v5",
            api_key=NVIDIA_API_KEY
        )
        
        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Create or get index
        index_name = "general-information-index"
        try:
            index = pc.Index(index_name)
        except:
            pc.create_index(
                    name="general-information-index",
                    dimension=1024,
                    metric='cosine',
                    spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                    )
                )
            index = pc.Index(index_name)
        
        print("\nChunks before indexing:")
        print("="*80)
        
        vectors = []
        for i, text in enumerate(resources_text):
            try:
                print(f"\nChunk {i}:")
                print(text)
                print("-"*40)
                
                # Generate embedding
                embedding = embeddings_client.embed_query(text)
                
                # Create vector
                vector = {
                    'id': f"resource_{i}",
                    'values': embedding,
                    'metadata': {
                        'text': text,
                        'source': 'graduate_resources'
                    }
                }
                vectors.append(vector)
                
                # Upsert in batches of 50
                if len(vectors) >= 50:
                    index.upsert(vectors=vectors)
                    print(f"Indexed batch of {len(vectors)} resources")
                    vectors = []
                    
            except Exception as e:
                print(f"Error processing resource {i}: {e}")
                continue
        
        # Upsert remaining vectors
        if vectors:
            index.upsert(vectors=vectors)
            print(f"Indexed final batch of {len(vectors)} resources")
        
        print("All resources have been indexed successfully!")
        
    except Exception as e:
        print(f"Error during indexing: {e}")

if __name__ == "__main__":
    print("Starting resource scraping...")
    resources_text = scrape_resources()
    
    if resources_text:
        print("\nStarting indexing process...")
        chunk_and_index_resources(resources_text)
    else:
        print("No resources to index")