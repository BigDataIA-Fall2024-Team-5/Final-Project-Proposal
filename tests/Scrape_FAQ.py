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

def chunk_text(text, max_length=500):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # Special handling for URLs and Q&A format
        if len(current_chunk) + len(sentence) < max_length or "http" in sentence or "Q:" in sentence:
            current_chunk += sentence + '. '
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + '. '
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def scrape_faq():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/faqs-for-newly-admitted-and-current-students/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        faq_text = []
        
        # Write title and introduction
        title = "FAQs for Newly Admitted and Current Students"
        intro = soup.find('p')
        if intro:
            faq_text.append(f"{title}\n\n{intro.text.strip()}\n\n")
        
        # Define sections
        sections = [
            "Course Registration",
            "Enrollment or Degree Verification",
            "Graduation",
            "Job Opportunities",
            "Stipend Graduate Assistantship (SGA)"
        ]
        
        print("\nRaw Data before chunking and indexing:")
        print("="*80)
        
        current_section = ""
        for q in soup.find_all(['b', 'strong']):
            question_text = q.text.strip()
            if question_text:
                qa_text = f"Q: {question_text}\n"
                
                # Get answer
                parent = q.find_parent()
                if parent:
                    # Extract links
                    links = []
                    for link in parent.find_all('a'):
                        if href := link.get('href'):
                            links.append(f"[{link.text.strip()}]({href})")
                    
                    # Get answer text
                    answer = parent.text.replace(q.text, "").strip()
                    qa_text += f"A: {answer}\n"
                    
                    # Add links
                    if links:
                        qa_text += "Links:\n"
                        for link in links:
                            qa_text += f"  {link}\n"
                
                print(qa_text)
                print("-"*80)
                faq_text.append(qa_text)
        
        # Save raw text
        with open('faq_content.txt', 'w', encoding='utf-8') as f:
            for text in faq_text:
                f.write(text + "\n")
        
        print(f"\nSuccessfully scraped FAQ content")
        return faq_text
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def chunk_and_index_faq(faq_text):
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
        
        vectors = []
        chunk_id = 0
        
        print("\nChunks before indexing:")
        print("="*80)
        
        for i, qa_pair in enumerate(faq_text):
            # Split into chunks while preserving Q&A format
            chunks = chunk_text(qa_pair)
            
            for chunk in chunks:
                if chunk.strip():
                    print(f"\nChunk {chunk_id}:")
                    print(chunk)
                    print("-"*40)
                    
                    try:
                        embedding = embeddings_client.embed_query(chunk)
                        
                        vector = {
                            'id': f"faq_{chunk_id}",
                            'values': embedding,
                            'metadata': {
                                'text': chunk,
                                'source': 'faq'
                            }
                        }
                        vectors.append(vector)
                        chunk_id += 1
                        
                        if len(vectors) >= 50:
                            index.upsert(vectors=vectors)
                            print(f"Indexed batch of {len(vectors)} chunks")
                            vectors = []
                            
                    except Exception as e:
                        print(f"Error processing chunk {chunk_id}: {e}")
                        continue
        
        # Upsert remaining vectors
        if vectors:
            index.upsert(vectors=vectors)
            print(f"Indexed final batch of {len(vectors)} chunks")
            
    except Exception as e:
        print(f"Error during indexing: {e}")

if __name__ == "__main__":
    print("Starting FAQ scraping...")
    faq_text = scrape_faq()
    
    if faq_text:
        print("\nStarting indexing process...")
        chunk_and_index_faq(faq_text)
    else:
        print("No FAQ content to index")