import boto3
import os
import time
import re
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        rows[row_index] = {}
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '
    return text


def get_textract_table_text(bucket_name, document_name, aws_access_key, aws_secret_key, aws_region):
    """
    Extract raw table text data from a PDF using AWS Textract.
    """
    client = boto3.client(
        'textract',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    response = client.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': document_name
            }
        },
        FeatureTypes=['TABLES']
    )

    job_id = response['JobId']
    print(f"Started Textract job with ID: {job_id}")

    # Wait for job completion
    while True:
        result = client.get_document_analysis(JobId=job_id)
        status = result['JobStatus']
        if status in ['SUCCEEDED', 'FAILED']:
            if status == 'FAILED':
                raise Exception("Textract job failed.")
            break
        print(f"Job status: {status}. Waiting for 5 seconds...")
        time.sleep(5)

    blocks = result['Blocks']
    blocks_map = {block['Id']: block for block in blocks}
    table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']

    if not table_blocks:
        raise ValueError("No tables found in the document.")

    combined_text = ""
    for table in table_blocks:
        rows = get_rows_columns_map(table, blocks_map)
        for row_index, cols in rows.items():
            combined_text += ','.join(cols[col].strip() for col in sorted(cols)) + '\n'

    return combined_text


def extract_user_profile_and_courses(data):
    """
    Extract user profile and completed courses from parsed Textract table data.
    """
    #print("\nDEBUG: Raw extracted text for matching:\n")
    #print(data)  # Debugging: Display raw text to help analyze matching patterns

    # Extract College and Program
    college_pattern = re.compile(r"College:\s*,(.*)")
    program_pattern = re.compile(r"Major and Department:\s*,(.*)")

    college_match = re.search(college_pattern, data)
    program_match = re.search(program_pattern, data)

    college = college_match.group(1).strip() if college_match else "Not Found"
    program = program_match.group(1).strip() if program_match else "Not Found"

    if not college_match:
        print("Warning: College information not found.")
    if not program_match:
        print("Warning: Program information not found.")

    # Extract GPA from Overall Section
    overall_gpa_pattern = re.compile(r"Overall:.*?,.*?,.*?,.*?,.*?,.*?,.*?,([\d.]+)")
    gpa_match = re.search(overall_gpa_pattern, data)
    gpa = float(gpa_match.group(1)) if gpa_match else None

    if not gpa_match:
        print("Warning: GPA information not found.")

    # Construct User Profile
    user_profile = {
        "user_id": 1,
        "username": "example_user",
        "password": "hashed_password_placeholder",
        "college": college,
        "program_id": program,
        "gpa": gpa if gpa else "Not Found",
        "campus": "example_campus",
    }

    # Extract Completed Courses
    course_pattern = re.compile(
        r"(\w+)\s*,(\d+)\s*,(GR|UG)\s*,([\w\s&\/\-]+)(?:,([A-F][+-]?|S|N/A))?,([\d.]+)?,?"
    )
    completed_courses = []

    for match in course_pattern.finditer(data):
        subject, course, level, title, grade, credits = match.groups()
        completed_courses.append({
            "user_id": user_profile["user_id"],
            "course_code": f"{subject} {course}",
            "course_name": title.strip(),
            "grade": grade if grade else "IP (In Progress)",
            "credits": float(credits) if credits else 0.0,
        })

    if not completed_courses:
        print("Warning: No completed courses found.")

    return user_profile, completed_courses


def main():
    bucket_name = os.getenv('S3_BUCKET_NAME')
    document_name = 'transcripts/1_transcript.pdf'
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')

    if not all([aws_access_key, aws_secret_key, aws_region]):
        raise EnvironmentError("Missing AWS credentials or region in environment variables.")

    # Extract table text using Textract
    try:
        table_text = get_textract_table_text(bucket_name, document_name, aws_access_key, aws_secret_key, aws_region)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Parse user profile and courses
    user_profile, completed_courses = extract_user_profile_and_courses(table_text)

    # Convert to DataFrames
    df_user_profile = pd.DataFrame([user_profile])
    df_completed_courses = pd.DataFrame(completed_courses)

    # Display the DataFrames
    print("\nUser Profile:")
    print(df_user_profile)
    print("\nCompleted Courses:")
    print(df_completed_courses)


if __name__ == "__main__":
    main()
