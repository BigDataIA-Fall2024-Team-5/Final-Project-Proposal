import requests
from bs4 import BeautifulSoup
import json
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            
        graduation_info = []
        
        # Process each section
        sections = soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol'])
        current_section = None
        
        for section in sections:
            if section.name == 'h1':
                if current_section:
                    graduation_info.append(current_section)
                current_section = {
                    'title': section.text.strip(),
                    'content': '',
                    'links': [],
                    'email_contacts': []
                }
            elif section.name in ['h2', 'h3', 'h4']:
                if current_section:
                    graduation_info.append(current_section)
                current_section = {
                    'title': section.text.strip(),
                    'content': '',
                    'links': [],
                    'email_contacts': []
                }
            elif current_section:
                # Handle both ordered and unordered lists
                if section.name in ['ol', 'ul']:
                    for item in section.find_all('li'):
                        current_section['content'] += "• " + item.text.strip() + '\n'
                        # Extract emails from list items
                        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', item.text)
                        if emails:
                            current_section['email_contacts'].extend(emails)
                else:
                    # Add content from paragraphs
                    content = section.text.strip()
                    if content:
                        current_section['content'] += content + '\n'
                
                # Extract links
                links = section.find_all('a')
                for link in links:
                    if href := link.get('href'):
                        current_section['links'].append({
                            'text': link.text.strip(),
                            'url': href
                        })
                
                # Extract emails from paragraphs
                if section.name == 'p':
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', content)
                    if emails:
                        current_section['email_contacts'].extend(emails)
        
        # Add the last section
        if current_section:
            graduation_info.append(current_section)
        
        # Clean up sections
        for section in graduation_info:
            # Clean up content
            section['content'] = section['content'].strip()
            # Remove duplicate emails
            if 'email_contacts' in section:
                section['email_contacts'] = list(set(section['email_contacts']))
            # Remove empty fields
            if not section['email_contacts']:
                del section['email_contacts']
            if not section['links']:
                del section['links']
            if not section['content']:
                del section['content']
        
        # Save to JSON file
        with open('graduation_info.json', 'w', encoding='utf-8') as f:
            json.dump(graduation_info, f, ensure_ascii=False, indent=4)
        
        print("Successfully scraped graduation information")
        print("\nContent of graduation_info.json:")
        print(json.dumps(graduation_info, indent=2))
        
        return graduation_info
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    scrape_graduation_info()