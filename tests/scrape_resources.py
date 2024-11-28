import requests
from bs4 import BeautifulSoup
import json
import re
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

def scrape_resources():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/university-graduate-resources/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove all script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Find the content area
        content = soup.find('div', {'class': ['content', 'content-area', 'main-content']})
        if not content:
            content = soup.find('main') or soup.find('article')
        
        resources = []
        
        if content:
            # Find all list items
            list_items = content.find_all('li')
            
            for li in list_items:
                resource = {
                    'title': '',
                    'description': '',
                    'links': [],
                    'phone_numbers': []
                }
                
                # Extract links and title
                links = li.find_all('a')
                if links:
                    resource['title'] = links[0].text.strip()
                    for link in links:
                        if href := link.get('href'):
                            resource['links'].append({
                                'text': link.text.strip(),
                                'url': href
                            })
                
                # Extract description
                text_content = li.get_text(separator=' ', strip=True)
                for link in links:
                    text_content = text_content.replace(link.text.strip(), '')
                resource['description'] = text_content.strip()
                
                # Extract phone numbers
                phone_numbers = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text_content)
                if phone_numbers:
                    resource['phone_numbers'] = list(set(phone_numbers))
                
                # Clean up empty fields
                if not resource['phone_numbers']:
                    del resource['phone_numbers']
                if not resource['links']:
                    del resource['links']
                if not resource['description']:
                    del resource['description']
                
                # Only add resources with content
                if len(resource) > 1:  # Must have more than just title
                    resources.append(resource)
        
        # Save and display results
        with open('graduate_resources.json', 'w', encoding='utf-8') as f:
            json.dump(resources, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully scraped {len(resources)} resources\n")
        print("Content of graduate_resources.json:")
        print(json.dumps(resources, indent=2))
        
        return resources
    
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == "__main__":
    scrape_resources()