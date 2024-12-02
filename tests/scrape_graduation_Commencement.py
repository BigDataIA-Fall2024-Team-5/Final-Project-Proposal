import requests
from bs4 import BeautifulSoup
import re
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys from environment variables
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

def scrape_graduation_info():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/graduation-commencement/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unnecessary elements
        for elem in soup(['script', 'style', 'nav', 'footer']):
            elem.decompose()
            
        graduation_text = []
        
        # Process each section
        sections = soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol'])
        current_section = None
        
        print("\nRaw Data before chunking and indexing:")
        print("="*80)
        
        for section in sections:
            section_text = ""
            
            if section.name in ['h1', 'h2', 'h3', 'h4']:
                section_text += f"\n{section.text.strip()}\n{'='*len(section.text.strip())}\n\n"
            else:
                if section.name in ['ol', 'ul']:
                    for item in section.find_all('li'):
                        section_text += f"• {item.text.strip()}\n"
                else:
                    section_text += f"{section.text.strip()}\n"
                
                # Extract links
                links = section.find_all('a')
                if links:
                    section_text += "Links:\n"
                    for link in links:
                        if href := link.get('href'):
                            section_text += f"- {link.text.strip()}: {href}\n"
            
            if section_text:
                print(section_text)
                graduation_text.append(section_text)
        
        # Save raw text
        with open('graduation_info.txt', 'w', encoding='utf-8') as f:
            for text in graduation_text:
                f.write(text + "\n")
        
        print(f"\nSuccessfully scraped graduation information")
        return graduation_text
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
def chunk_text(text, max_length=500):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # Special handling for URLs - keep them intact
        if len(current_chunk) + len(sentence) < max_length or "http" in sentence:
            current_chunk += sentence + '. '
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + '. '
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
def chunk_and_index_graduation(graduation_text):
    try:
        # Initialize NVIDIA embeddings
        embeddings_client = NVIDIAEmbeddings(
            model="nvidia/nv-embedqa-e5-v5",
            api_key=NVIDIA_API_KEY
        )
        
        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Create or get index
        index_name = "graduateresources"
        try:
            index = pc.Index(index_name)
        except:
            pc.create_index(
                name=index_name,
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
        chunk_id = 0
        for i, section in enumerate(graduation_text):
            # Split section into smaller chunks
            chunks = chunk_text(section)
            
            for chunk in chunks:
                    if chunk.strip():  # Skip empty chunks
                        print(f"Chunk {chunk_id}:")
                        print(chunk)
                        print("-"*40)
            try:
                        embedding = embeddings_client.embed_query(chunk)
                        
                        vector = {
                            'id': f"graduation_{i}_{chunk_id}",
                            'values': embedding,
                            'metadata': {
                                'text': chunk,
                                'source': 'graduation_commencement',
                                'section_id': i
                            }
                        }
                        vectors.append(vector)
                        chunk_id += 1
                        
                        if len(vectors) >= 50:
                            index.upsert(vectors=vectors)
                            print(f"Indexed batch of {len(vectors)} chunks")
                            vectors = []
                            
            except Exception as e:
                    print(f"Error processing chunk {chunk_id} of section {i}: {e}")
                    continue
        
        # Upsert remaining vectors
        if vectors:
            index.upsert(vectors=vectors)
            print(f"Indexed final batch of {len(vectors)} chunks")
            
    except Exception as e:
        print(f"Error during indexing: {e}")

if __name__ == "__main__":
    print("Starting graduation information scraping...")
    graduation_text = scrape_graduation_info()
    
    if graduation_text:
        print("\nStarting indexing process...")
        chunk_and_index_graduation(graduation_text)
    else:
        print("No graduation information to index")