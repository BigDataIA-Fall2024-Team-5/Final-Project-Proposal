from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
import boto3
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from routers.auth import validate_jwt
import snowflake.connector

# Load environment variables
load_dotenv()

# Initialize router
transcript_router = APIRouter()

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# Snowflake Configuration
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
    )

# Validate PDF file
def validate_pdf(file: UploadFile):
    try:
        header = file.file.read(5)
        if header != b'%PDF-':
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")

        file.file.seek(0)  # Reset file pointer
        pdf_reader = PdfReader(file.file)
        if len(pdf_reader.pages) > 10:
            raise HTTPException(status_code=400, detail="PDF must not exceed 10 pages.")

        file.file.seek(0)  # Reset file pointer for further operations
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")

# Upload file to S3
def upload_to_s3(file: UploadFile, user_id: int):
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )

        file_path = f"transcripts/{user_id}_transcript.pdf"
        s3.upload_fileobj(file.file, S3_BUCKET_NAME, file_path)

        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_path}"
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": file_path},
            ExpiresIn=3600,
        )
        return presigned_url, file_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to S3: {str(e)}")

from fastapi import HTTPException, UploadFile
import boto3
import re
import time
import pandas as pd
from typing import Tuple, List, Dict

# Helper functions for processing AWS Textract results
def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    for relationship in table_result.get("Relationships", []):
        if relationship["Type"] == "CHILD":
            for child_id in relationship["Ids"]:
                cell = blocks_map[child_id]
                if cell["BlockType"] == "CELL":
                    row_index = cell["RowIndex"]
                    col_index = cell["ColumnIndex"]
                    if row_index not in rows:
                        rows[row_index] = {}
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows


def get_text(result, blocks_map):
    text = ""
    if "Relationships" in result:
        for relationship in result["Relationships"]:
            if relationship["Type"] == "CHILD":
                for child_id in relationship["Ids"]:
                    word = blocks_map[child_id]
                    if word["BlockType"] == "WORD":
                        text += word["Text"] + " "
                    elif word["BlockType"] == "SELECTION_ELEMENT":
                        if word["SelectionStatus"] == "SELECTED":
                            text += "X "
    return text


def get_textract_table_text(bucket_name: str, document_name: str, aws_access_key: str, aws_secret_key: str, aws_region: str) -> str:
    client = boto3.client(
        "textract",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region,
    )

    response = client.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": bucket_name, "Name": document_name}},
        FeatureTypes=["TABLES"],
    )

    job_id = response["JobId"]

    # Wait for job completion
    while True:
        result = client.get_document_analysis(JobId=job_id)
        status = result["JobStatus"]
        if status in ["SUCCEEDED", "FAILED"]:
            if status == "FAILED":
                raise HTTPException(status_code=500, detail="AWS Textract job failed.")
            break
        time.sleep(5)

    blocks = result["Blocks"]
    blocks_map = {block["Id"]: block for block in blocks}
    table_blocks = [block for block in blocks if block["BlockType"] == "TABLE"]

    if not table_blocks:
        raise HTTPException(status_code=400, detail="No tables found in the document.")

    combined_text = ""
    for table in table_blocks:
        rows = get_rows_columns_map(table, blocks_map)
        for row_index, cols in rows.items():
            combined_text += ",".join(cols[col].strip() for col in sorted(cols)) + "\n"

    return combined_text


def extract_user_profile_and_courses(data: str) -> Tuple[Dict, List[Dict]]:
    college_pattern = re.compile(r"College:\s*,(.*)")
    program_pattern = re.compile(r"Major and Department:\s*,(.*)")
    overall_gpa_pattern = re.compile(r"Overall:.*?,.*?,.*?,.*?,.*?,.*?,.*?,([\d.]+)")

    college_match = re.search(college_pattern, data)
    program_match = re.search(program_pattern, data)
    gpa_match = re.search(overall_gpa_pattern, data)

    college = college_match.group(1).strip() if college_match else "Not Found"
    program = program_match.group(1).strip() if program_match else "Not Found"
    gpa = float(gpa_match.group(1)) if gpa_match else None

    user_profile = {
        "college": college,
        "program_id": program,
        "gpa": gpa if gpa else "Not Found",
    }

    course_pattern = re.compile(
        r"(\w+)\s*,(\d+)\s*,(GR|UG)\s*,([\w\s&\/\-]+)(?:,([A-F][+-]?|S|N/A))?,([\d.]+)?,?"
    )
    completed_courses = []

    for match in course_pattern.finditer(data):
        subject, course, level, title, grade, credits = match.groups()
        completed_courses.append({
            "course_code": f"{subject} {course}",
            "course_name": title.strip(),
            "grade": grade if grade else "IP (In Progress)",
            "credits": float(credits) if credits else 0.0,
        })

    return user_profile, completed_courses


# Updated process_transcript function
def process_transcript(file_url: str) -> Tuple[List[Dict], Dict]:
    # Parse the bucket name and file key from the file_url
    match = re.match(r"https://(.*)\.s3\.(.*?)\.amazonaws\.com/(.*)", file_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid S3 file URL.")

    bucket_name = match.group(1)
    aws_region = match.group(2)
    file_key = match.group(3)

    # Validate AWS credentials
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not all([aws_access_key, aws_secret_key, aws_region]):
        raise HTTPException(status_code=500, detail="AWS credentials or region are not set.")

    try:
        # Extract table text from AWS Textract
        table_text = get_textract_table_text(bucket_name, file_key, aws_access_key, aws_secret_key, aws_region)

        # Extract user profile and completed courses
        user_profile, completed_courses = extract_user_profile_and_courses(table_text)

        # Compile additional details
        additional_details = {
            "courses_detected": len(completed_courses),
            "user_profile": user_profile,
        }

        return completed_courses, additional_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process transcript: {str(e)}")



# Save transcript link to Snowflake
def save_transcript_link_to_snowflake(user_id: int, file_url: str):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE USER_PROFILE
            SET TRANSCRIPT_LINK = %s
            WHERE USER_ID = %s
            """,
            (file_url, user_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to update transcript link in database.")
    finally:
        cursor.close()
        conn.close()

# Endpoint to fetch transcript link
@transcript_router.get("/transcript_link/{user_id}")
async def get_transcript_link(user_id: int, jwt_token: str = Depends(validate_jwt)):
    if jwt_token["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT TRANSCRIPT_LINK
            FROM USER_PROFILE
            WHERE USER_ID = %s
            """,
            (user_id,),
        )
        result = cursor.fetchone()
        if result and result[0]:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION,
            )
            # Extract the file path from the URL
            file_key = result[0].replace(f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/", "")
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET_NAME, "Key": file_key},
                ExpiresIn=3600,
            )
            return {"transcript_presigned_url": presigned_url}
        else:
            return {"message": "No transcript found for this user."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch transcript link.")
    finally:
        cursor.close()
        conn.close()

# Endpoint to upload and process transcript
@transcript_router.post("/upload_transcript")
async def upload_transcript(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    jwt_token: str = Depends(validate_jwt),
):
    # Validate user access
    if jwt_token["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # Validate PDF structure and size
    validate_pdf(file)

    # Upload file to S3 and retrieve URLs
    presigned_url, file_url = upload_to_s3(file, user_id)

    # Process transcript using the S3 file path
    courses, additional_details = process_transcript(file_url)

    # Save the transcript link to Snowflake for the user
    save_transcript_link_to_snowflake(user_id, file_url)

    # Return response
    return {
        "message": "Transcript processed successfully.",
        "transcript_presigned_url": presigned_url,
        "courses": courses,
        "additional_details": additional_details,
    }

