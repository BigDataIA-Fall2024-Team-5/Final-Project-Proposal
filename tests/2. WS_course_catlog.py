import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Function to clean up text (remove special characters and normalize spaces)
def clean_text(text):
    if text:
        text = text.replace('\xa0', ' ').replace('Â', '').strip()
        text = re.sub(r'\s+', ' ', text)
        # Add missing spaces after course codes like INFO 5100
        text = re.sub(r'([A-Z]{4,}\s\d{4})(?=[A-Za-z])', r'\1 ', text)
        text = re.sub(r'(\bor)([A-Z])', r'\1 \2', text)  # Fix missing space after 'or'
        return text
    return None

# Function to clean title and remove unwanted parts like "(4 Hours)"
def clean_title(title):
    title = re.sub(r'\(\d+(-\d+)? Hours\)', '', title).strip()
    title = title.rstrip('.')
    return title

# Function to process credit hours
def process_credit_hours(title):
    match = re.search(r'\((\d+)(?:-(\d+))? Hours\)', title)
    if match:
        if match.group(2):  # Handle ranges like "1-4"
            return f"{match.group(1)} to {match.group(2)}"
        return match.group(1)  # Single value like "4"
    return "0"

# Function to extract prerequisites or corequisites
def extract_requisites(block, key):
    requisite_blocks = block.find_all('p', class_='courseblockextra')
    requisite_texts = []
    for requisite_block in requisite_blocks:
        if key in requisite_block.get_text():
            # Get the entire text of the block, which includes all tags
            raw_text = requisite_block.get_text(" ", strip=True)
            # Remove the 'Prerequisite(s):' or 'Corequisite(s):' prefix
            requisite_text = raw_text.replace(f'{key}(s):', '').strip()
            requisite_texts.append(clean_text(requisite_text))
    # Join all requisite texts with " AND " if multiple requisite blocks are present
    return " AND ".join(requisite_texts) if requisite_texts else None

# Main function
def main(subject_codes, output_filename):
    # Prepare list to store course data
    data = []
    
    for subject_code in subject_codes:
        # Define the URL dynamically based on subject code
        url = f"https://catalog.northeastern.edu/course-descriptions/{subject_code}/"
        
        # Send HTTP request
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch data for subject code: {subject_code}. HTTP Status Code: {response.status_code}")
            continue
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Iterate over each course block
        course_blocks = soup.find_all('div', class_='courseblock')
        for block in course_blocks:
            try:
                # Extract course code and title
                course_title = block.find('p', class_='courseblocktitle').get_text(strip=True)
                course_title = clean_text(course_title)
                
                # Process credit hours
                credit_hours = process_credit_hours(course_title)

                # Remove credit hours from the title
                course_title = clean_title(course_title)
                course_code, title = course_title.split('.', 1)
                course_code = course_code.strip()
                title = title.strip()

                # Extract description
                description = block.find('p', class_='cb_desc')
                description = clean_text(description.get_text(strip=True)) if description else None

                # Extract prerequisites and corequisites
                prerequisites = extract_requisites(block, 'Prerequisite')
                corequisites = extract_requisites(block, 'Corequisite')

                # Extract subject code
                subject_code_upper = course_code.split(' ')[0]

                # Append the course data to the list
                data.append({
                    'course_code': course_code,
                    'title': title,
                    'description': description,
                    'prerequisites': prerequisites,
                    'corequisites': corequisites,
                    'credit_hours': credit_hours,
                    'subject_code': subject_code_upper
                })
            except Exception as e:
                print(f"Error processing course block: {block}. Error: {e}")
    
    # Convert data to a DataFrame
    df = pd.DataFrame(data)

    # Save DataFrame to CSV
    df.to_csv(output_filename, index=False, encoding='utf-8')
    print(f"Data saved to {output_filename}")

# Entry point of the script
if __name__ == "__main__":
    subject_codes = ["info", "damg","tele","csye"]
    output_filename = "all_courses.csv"
    main(subject_codes, output_filename)
