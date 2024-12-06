import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import boto3
from io import StringIO
import os

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
    title = re.sub(r'\(\d+(-\d+)?\sHour(?:s)?\)', '', title).strip()
    title = title.rstrip('.')
    return title

# Function to extract credit hours
def process_credit_hours(title):
    match = re.search(r'\((\d+)(?:-(\d+))?\sHour(?:s)?\)', title)
    if match:
        if match.group(2):
            return float(match.group(2))
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

# Combined function to scrape data and save to S3
def scrape_and_save_to_s3(subject_codes, bucket_name, s3_key):
    data = []
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
                course_title = block.find('p', class_='courseblocktitle').get_text(strip=True)
                course_title = clean_text(course_title)
                credit_hours = process_credit_hours(course_title)
                course_title = clean_title(course_title)
                course_code, title = course_title.split('.', 1)
                course_code = course_code.strip()
                title = title.strip()

                description = block.find('p', class_='cb_desc')
                description = clean_text(description.get_text(strip=True)) if description else None

                prerequisites = extract_requisites(block, 'Prerequisite')
                corequisites = extract_requisites(block, 'Corequisite')

                subject_code_upper = course_code.split(' ')[0]

                data.append({
                    'COURSE_CODE': course_code,
                    'COURSE_NAME': title,
                    'DESCRIPTION': description,
                    'PREREQUISITES': prerequisites,
                    'COREQUISITES': corequisites,
                    'CREDITS': credit_hours,
                    'SUBJECT_CODE': subject_code_upper
                })
                print(f"Processed course: {course_code} - {title}")
            except Exception as e:
                print(f"Error processing course block: {block}. Error: {e}")
    
    print(f"Scraping completed. Total courses scraped: {len(data)}")
    
    # Convert data to DataFrame
    df = pd.DataFrame(data)

    # Save to S3
    print("Saving data to S3...")
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue()
        )
        print(f"File uploaded to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Error uploading to S3: {e}")

    return df  # Return DataFrame for further processing if needed
