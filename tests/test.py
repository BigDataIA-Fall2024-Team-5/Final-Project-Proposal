import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

# Function to clean text
def clean_text(text):
    if text:
        text = text.replace('\xa0', ' ').replace('Â', '').strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([A-Z]{4,}\s\d{4})(?=[A-Za-z])', r'\1 ', text)
        text = re.sub(r'(\bor)([A-Z])', r'\1 \2', text)
        return text
    return None

# Function to clean title
def clean_title(title):
    # Match both 'Hour' and 'Hours' in the pattern
    title = re.sub(r'\(\d+(-\d+)?\sHour(?:s)?\)', '', title).strip()
    title = title.rstrip('.')
    return title

def process_credit_hours(title):
    # Match both 'Hour' and 'Hours' in the pattern
    match = re.search(r'\((\d+)(?:-(\d+))?\sHour(?:s)?\)', title)
    if match:
        if match.group(2):
            return float(match.group(2))  # Take the maximum of the range
        return float(match.group(1))
    return 0.0


# Function to extract prerequisites or corequisites
def extract_requisites(block, key):
    requisite_blocks = block.find_all('p', class_='courseblockextra')
    requisite_texts = []
    for requisite_block in requisite_blocks:
        if key in requisite_block.get_text():
            raw_text = requisite_block.get_text(" ", strip=True)
            requisite_text = raw_text.replace(f'{key}(s):', '').strip()
            requisite_texts.append(clean_text(requisite_text))
    return " AND ".join(requisite_texts) if requisite_texts else None

# Function to scrape course data
def scrape_course_data(subject_codes):
    for subject_code in subject_codes:
        print(f"Scraping data for subject code: {subject_code}")
        url = f"https://catalog.northeastern.edu/course-descriptions/{subject_code}/"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch data for subject code: {subject_code}. HTTP Status Code: {response.status_code}")
            continue

        soup = BeautifulSoup(response.content, "html.parser")
        course_blocks = soup.find_all('div', class_='courseblock')
        print(f"Found {len(course_blocks)} courses for subject code: {subject_code}")
        for block in course_blocks:
            try:
                # Extract course code and title
                course_title = block.find('p', class_='courseblocktitle').get_text(strip=True)
                course_title = clean_text(course_title)
                credit_hours = process_credit_hours(course_title)
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

                # Print extracted data
                print(f"Course Code: {course_code}")
                print(f"Title: {title}")
                print(f"Credits: {credit_hours}")
                print(f"Description: {description}")
                print(f"Prerequisites: {prerequisites}")
                print(f"Corequisites: {corequisites}")
                print(f"Subject Code: {subject_code_upper}")
                print("-" * 50)
            except Exception as e:
                print(f"Error processing course block. Error: {e}")
                print("-" * 50)

# Main function
def main(subject_codes):
    print("Starting the scraping process...")
    scrape_course_data(subject_codes)
    print("Scraping process completed.")

# Execute script
if __name__ == "__main__":
    subject_codes = ["info","encp"]  # Replace with desired subject codes
    main(subject_codes)