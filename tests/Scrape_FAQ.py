import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_faq():
    url = "https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-student-services/faqs-for-newly-admitted-and-current-students/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Open file for writing
        with open('faq_content.txt', 'w', encoding='utf-8') as f:
            # Write title and introduction
            f.write("FAQs for Newly Admitted and Current Students\n\n")
            intro = soup.find('p')
            if intro:
                f.write(f"{intro.text.strip()}\n\n")
            
            # Define sections
            sections = [
                "Course Registration",
                "Enrollment or Degree Verification",
                "Graduation",
                "Job Opportunities",
                "Stipend Graduate Assistantship (SGA)"
            ]
            
            # Write section headers
            for section in sections:
                f.write(f"\n{section}\n{'='*len(section)}\n\n")
            
            # Find all questions and answers
            for q in soup.find_all(['b', 'strong']):
                question_text = q.text.strip()
                if question_text:
                    f.write(f"Q: {question_text}\n")
                    
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
                        f.write(f"A: {answer}\n")
                        
                        # Write links
                        if links:
                            f.write("Links:\n")
                            for link in links:
                                f.write(f"  {link}\n")
                        f.write("\n")
            
            # Find and write SGA steps separately
            sga_steps = soup.find_all('strong', string=lambda s: s and 'Step' in s)
            for step in sga_steps:
                step_text = step.text.strip()
                if step_text:
                    f.write(f"\n{step_text}:\n")
                    next_text = step.next_sibling
                    if next_text:
                        f.write(f"{next_text.strip()}\n")
        
        print("FAQ content has been saved to faq_content.txt")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    scrape_faq()