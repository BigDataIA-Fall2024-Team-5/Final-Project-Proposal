import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import boto3
import os
import snowflake.connector
from io import StringIO
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv

load_dotenv()
# Initialize Pinecone client
pc = PineconeClient(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize NVIDIA embedding client
embedding_client = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END"  # Adjust truncate settings based on model requirements
)


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
    title = re.sub(r'\(\d+(-\d+)? Hours\)', '', title).strip()
    title = title.rstrip('.')
    return title

# Function to process credit hours
def process_credit_hours(title):
    match = re.search(r'\((\d+)(?:-(\d+))? Hours\)', title)
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

                # Append data
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
    return pd.DataFrame(data)

# Save DataFrame to S3
def save_to_s3_in_memory(df, bucket_name, s3_key):
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

# Insert data into Snowflake
def insert_data_to_snowflake(df):
    print("Inserting data into Snowflake directly...")
    try:
        # Establish Snowflake connection
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
            database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
        )
        cursor = conn.cursor()

        # Define the target table
        table_name = "COURSE_CATALOG"

        # Convert the DataFrame to CSV format in memory
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, header=False)  # Exclude headers for Snowflake COPY
        csv_buffer.seek(0)

        # Upload DataFrame to Snowflake using Snowflake's `MERGE`
        print(f"Creating temporary table TEMP_{table_name}...")
        cursor.execute(f"CREATE TEMPORARY TABLE IF NOT EXISTS TEMP_{table_name} LIKE {table_name};")
        print(f"Temporary table TEMP_{table_name} created.")

        print("Uploading data to Snowflake temporary table...")
        for _, row in df.iterrows():
            cursor.execute(
                f"""
                INSERT INTO TEMP_{table_name}
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["COURSE_CODE"],
                    row["COURSE_NAME"],
                    row["DESCRIPTION"],
                    row["PREREQUISITES"],
                    row["COREQUISITES"],
                    row["CREDITS"],
                    row["SUBJECT_CODE"],
                ),
            )

        print("Data uploaded to temporary table.")

        # Merge data into the target table
        print(f"Merging data into {table_name}...")
        cursor.execute(f"""
            MERGE INTO {table_name} AS target
            USING TEMP_{table_name} AS source
            ON target.COURSE_CODE = source.COURSE_CODE
            WHEN MATCHED THEN UPDATE SET
                COURSE_NAME = source.COURSE_NAME,
                DESCRIPTION = source.DESCRIPTION,
                PREREQUISITES = source.PREREQUISITES,
                COREQUISITES = source.COREQUISITES,
                CREDITS = source.CREDITS,
                SUBJECT_CODE = source.SUBJECT_CODE
            WHEN NOT MATCHED THEN INSERT (
                COURSE_CODE, COURSE_NAME, DESCRIPTION, PREREQUISITES, COREQUISITES, CREDITS, SUBJECT_CODE
            ) VALUES (
                source.COURSE_CODE, source.COURSE_NAME, source.DESCRIPTION, source.PREREQUISITES, source.COREQUISITES, source.CREDITS, source.SUBJECT_CODE
            );
        """)
        print(f"Data merged successfully into {table_name}.")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting data to Snowflake: {e}")

def create_index_in_pinecone():
    """
    Create or reset the Pinecone index for course catalog data.
    """
    index_name = "course-catalog-index"

    # Check and delete existing index
    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")

    # Create the index
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1024,  
            metric="cosine", 
            spec=ServerlessSpec(cloud="aws", region="us-east-1") 
        )
        print(f"Created new index: {index_name}")

    # Connect to the index
    pinecone_index = pc.Index(index_name)
    return pinecone_index

def add_course_data_to_index(pinecone_index, df):
    """
    Add course data to the Pinecone index.
    
    Args:
        pinecone_index: The Pinecone index object.
        df: DataFrame containing course data.
    """
    print("Adding course data to Pinecone index...")

    for _, row in df.iterrows():
        try:
            # Prepare chunk content for embedding
            chunk_content = (
                f"COURSE_CODE: {row['COURSE_CODE']}\n"
                f"COURSE_NAME: {row['COURSE_NAME']}\n"
                f"DESCRIPTION: {row['DESCRIPTION']}\n"
            )

            # Generate embedding using NVIDIA API
            embedding = embedding_client.embed_query(chunk_content)

            # Metadata for the embedding
            metadata = {
                "course_code": row["COURSE_CODE"],
                "course_name": row["COURSE_NAME"],
                "description": row['DESCRIPTION'] or "No description available",
                "prerequisites": row['PREREQUISITES'] or "None",
                "corequisites": row['COREQUISITES'] or "None",
                "credits": row["CREDITS"],
                "subject_code": row["SUBJECT_CODE"],
            }

            # Upsert the embedding into Pinecone
            pinecone_index.upsert([
                {"id": row["COURSE_CODE"], "values": embedding, "metadata": metadata}
            ])
            print(f"Stored or updated embedding for course: {row['COURSE_CODE']}")
        except Exception as e:
            print(f"Error storing data for course {row['COURSE_CODE']}: {e}")


# Main function
def main(subject_codes):
    print("Starting the scraping process...")
    # Scrape data
    df = scrape_course_data(subject_codes)

    # Save to S3
    s3_key = "neu_data/all_courses.csv"
    save_to_s3_in_memory(df, os.getenv("S3_BUCKET_NAME"), s3_key)

    # Insert into Snowflake
    insert_data_to_snowflake(df)
    print("Process completed successfully.")

    pinecone_index = create_index_in_pinecone()

    add_course_data_to_index(pinecone_index, df)

# Execute script
if __name__ == "__main__":
    subject_codes = ["info", "damg", "tele", "csye"]
    main(subject_codes)
