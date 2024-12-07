import requests
from bs4 import BeautifulSoup
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
urllib3.disable_warnings(InsecureRequestWarning)

def scrape_graduation_info():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/graduation-commencement/"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unnecessary elements
        for elem in soup(['script', 'style', 'nav', 'footer']):
            elem.decompose()
            
        # Find main content area
        content = soup.find('div', {'class': ['content', 'content-area', 'main-content']})
        if not content:
            content = soup.find('main') or soup.find('article')
        
        # Define logical sections based on the actual content structure
        sections = {
            'main': {
                'title': 'Graduation / Commencement',
                'content': [],
                'links': []
            },
            'apply': {
                'title': 'How to Apply to Graduate',
                'content': [],
                'links': []
            },
            'special_programs': {
                'title': 'Special Program Requirements',
                'content': [],
                'links': []
            },
            'clearance': {
                'title': 'Graduation Clearance Procedures',
                'content': [],
                'links': []
            },
            'resources': {
                'title': "Master's Thesis and PhD Dissertation Resources",
                'content': [],
                'links': []
            }
        }
        
        current_section = 'main'
        bullet_group = []
        
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol']):
            text = element.text.strip()
            
            # Determine section based on content markers
            if 'How to Apply' in text:
                current_section = 'apply'
            elif 'Clearance Procedures' in text:
                current_section = 'clearance'
            elif 'Thesis' in text or 'Dissertation' in text:
                current_section = 'resources'
            elif any(x in text for x in ['BS/MS', 'certificate program']):
                current_section = 'special_programs'
            
            # Handle content
            if element.name in ['ul', 'ol']:
                bullet_points = []
                for item in element.find_all('li'):
                    bullet_points.append(f"• {item.text.strip()}")
                if bullet_points:
                    sections[current_section]['content'].extend(bullet_points)
            else:
                if text and not any(text.endswith(x) for x in ['=', '==']):
                    sections[current_section]['content'].append(text)
            
            # Handle links
            for link in element.find_all('a'):
                if href := link.get('href'):
                    sections[current_section]['links'].append({
                        'text': link.text.strip(),
                        'url': href
                    })
        
        return sections
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def create_chunks(sections, max_length=600):
    chunks = []
    
    for section_name, section in sections.items():
        if not section['content']:
            continue
            
        current_chunk = f"{section['title']}\n{'='*len(section['title'])}\n\n"
        content_buffer = []
        
        for content in section['content']:
            # Group bullet points together
            if content.startswith('•'):
                if content_buffer:
                    chunk_text = '\n'.join(content_buffer)
                    if len(current_chunk) + len(chunk_text) > max_length:
                        chunks.append(current_chunk.strip())
                        current_chunk = f"{section['title']}\n{'='*len(section['title'])}\n\n{chunk_text}\n"
                    else:
                        current_chunk += chunk_text + '\n'
                    content_buffer = []
                
                if len(current_chunk) + len(content) > max_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = f"{section['title']}\n{'='*len(section['title'])}\n\n{content}\n"
                else:
                    current_chunk += content + '\n'
            else:
                content_buffer.append(content)
        
        # Process any remaining content
        if content_buffer:
            chunk_text = '\n'.join(content_buffer)
            if len(current_chunk) + len(chunk_text) > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = f"{section['title']}\n{'='*len(section['title'])}\n\n{chunk_text}\n"
            else:
                current_chunk += chunk_text + '\n'
        
        # Add links at the end of the section
        if section['links']:
            links_text = "\nLinks:\n" + "\n".join(
                f"- {link['text']}: {link['url']}" 
                for link in section['links']
            )
            
            if len(current_chunk) + len(links_text) > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = links_text
            else:
                current_chunk += links_text
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
    
    return chunks

def chunk_and_index_graduation(sections):
    try:
        embeddings_client = NVIDIAEmbeddings(
            model="nvidia/nv-embedqa-e5-v5",
            api_key=NVIDIA_API_KEY
        )
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index_name = "general-information-index"
        
        try:
            index = pc.Index(index_name)
        except Exception as e:
            print(f"Creating new index due to: {e}")
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
        
        chunks = create_chunks(sections)
        vectors = []
        
        for chunk_id, chunk in enumerate(chunks):
            if chunk.strip():
                print(f"\nChunk {chunk_id}:")
                print(chunk)
                print("-"*40)
                
                try:
                    embedding = embeddings_client.embed_query(chunk)
                    vector = {
                        'id': f"graduation_{chunk_id}",
                        'values': embedding,
                        'metadata': {
                            'text': chunk,
                            'source': 'graduation_commencement'
                        }
                    }
                    vectors.append(vector)
                    
                    if len(vectors) >= 50:
                        index.upsert(vectors=vectors)
                        print(f"Indexed batch of {len(vectors)} chunks")
                        vectors = []
                        
                except Exception as e:
                    print(f"Error processing chunk {chunk_id}: {e}")
                    continue
        
        if vectors:
            index.upsert(vectors=vectors)
            print(f"Indexed final batch of {len(vectors)} chunks")
            
    except Exception as e:
        print(f"Error during indexing: {e}")
if __name__ == "__main__":
    print("Starting graduation information scraping...")
    sections = scrape_graduation_info()
    
    if sections:
        print("\nStarting indexing process...")
        chunk_and_index_graduation(sections)
    else:
        print("No graduation information to index")