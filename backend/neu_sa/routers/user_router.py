from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import snowflake.connector
from neu_sa.routers.auth import validate_jwt
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()

# Initialize router
user_router = APIRouter()

# Predefined values
VALID_CAMPUSES = [
    "Boston",
    "Online",
    "Seattle, WA",
    "Silicon Valley, CA",
    "Oakland, CA",
    "Arlington, VA",
    "Miami, FL",
    "Toronto, Canada",
    "Vancouver, Canada",
]

PROGRAM_ID_MAP = {
    "Information Systems, MSIS": "MP_IS_MSIS",
    "Cyber-Physical Systems, MS": "MP_CPS_MS",
    "Data Architecture and Management, MS": "MP_DAM_MS",
    "Software Engineering Systems, MS": "MP_SES_MS",
    "Telecommunication Networks, MS": "MP_TN_MS",
}

VALID_PROGRAM_NAMES = list(PROGRAM_ID_MAP.keys())

VALID_COLLEGES = [
    "College of Engineering",
]

# Snowflake connection
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
    )

# Models
class UserProfile(BaseModel):
    college: str
    program_name: str
    program_id: str
    gpa: float
    campus: str
    transcript_link: str = ""

class UserCourse(BaseModel):
    course_code: str
    course_name: str
    grade: str
    credits: float

# Fetch user profile and courses
def fetch_user_data_from_snowflake(user_id: int):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COLLEGE, PROGRAM_NAME, PROGRAM_ID, GPA, CAMPUS, TRANSCRIPT_LINK
            FROM USER_PROFILE
            WHERE USER_ID = %s
            """,
            (user_id,)
        )
        profile_result = cursor.fetchone()
        if not profile_result:
            user_profile = {
                "college": "Not Provided",
                "program_name": "Not Provided",
                "program_id": "Not Provided",
                "gpa": 0.0,
                "campus": "Not Provided",
                "transcript_link": "",
            }
        else:
            user_profile = {
                "college": profile_result[0] or "Not Provided",
                "program_name": profile_result[1] or "Not Provided",
                "program_id": profile_result[2] or "Not Provided",
                "gpa": profile_result[3] or 0.0,
                "campus": profile_result[4] or "Not Provided",
                "transcript_link": profile_result[5] or "",
            }

        cursor.execute(
            """
            SELECT COURSE_CODE, COURSE_NAME, GRADE, CREDITS
            FROM USER_COURSES
            WHERE USER_ID = %s
            """,
            (user_id,)
        )
        courses_result = cursor.fetchall()
        courses = [
            {"course_code": row[0], "course_name": row[1], "grade": row[2], "credits": row[3]}
            for row in courses_result
        ] if courses_result else []

        return {"profile": user_profile, "courses": courses}
    finally:
        cursor.close()
        conn.close()

# Endpoint: Get user data
@user_router.get("/{user_id}")
async def get_user_data(user_id: int, jwt_token: str = Depends(validate_jwt)):
    if jwt_token["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    user_data = fetch_user_data_from_snowflake(user_id)
    return user_data

# Endpoint: Update user profile
@user_router.put("/{user_id}/profile")
async def update_user_profile(user_id: int, user_profile: UserProfile, jwt_token: str = Depends(validate_jwt)):
    if jwt_token["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    if user_profile.campus not in VALID_CAMPUSES:
        raise HTTPException(status_code=400, detail="Invalid campus selected.")

    if user_profile.program_name not in VALID_PROGRAM_NAMES:
        raise HTTPException(status_code=400, detail="Invalid program name selected.")

    if user_profile.college not in VALID_COLLEGES:
        raise HTTPException(status_code=400, detail="Invalid college selected.")

    # Validate GPA
    if user_profile.gpa < 0.0 or user_profile.gpa > 4.0:
        raise HTTPException(status_code=400, detail="GPA must be between 0.0 and 4.0.")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE USER_PROFILE
            SET COLLEGE = %s, PROGRAM_NAME = %s, PROGRAM_ID = %s, GPA = %s, CAMPUS = %s
            WHERE USER_ID = %s
            """,
            (
                user_profile.college,
                user_profile.program_name,
                PROGRAM_ID_MAP[user_profile.program_name],
                user_profile.gpa,
                user_profile.campus,
                user_id,
            )
        )
        conn.commit()
        return {"message": "User profile updated successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# Endpoint: Update user courses
@user_router.put("/{user_id}/courses")
async def update_user_courses(user_id: int, courses: List[UserCourse], jwt_token: str = Depends(validate_jwt)):
    if jwt_token["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    VALID_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "F","S","IP (In Progress)"}
    VALID_CREDITS = {0, 1, 2, 3, 4}  # Valid credits: 0, 1, 2, 3, 4

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        # Convert incoming courses to a set of course codes
        incoming_course_codes = {course.course_code for course in courses}

        # Fetch existing courses for the user
        cursor.execute(
            """
            SELECT course_code
            FROM USER_COURSES
            WHERE user_id = %s
            """,
            (user_id,),
        )
        existing_courses = {row[0] for row in cursor.fetchall()}

        # Find courses to remove (existing courses not in incoming courses)
        courses_to_remove = existing_courses - incoming_course_codes

        # Remove unlisted courses from the database
        if courses_to_remove:
            cursor.executemany(
                """
                DELETE FROM USER_COURSES
                WHERE user_id = %s AND course_code = %s
                """,
                [(user_id, course_code) for course_code in courses_to_remove],
            )
            conn.commit()

        # Validate and update or insert incoming courses
        for course in courses:
            # Validate course details
            if not re.match(r"^[A-Z]{4} \d{4}$", course.course_code):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid course code format: {course.course_code}. Expected format: 'INFO 5490'.",
                )
            if course.grade not in VALID_GRADES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid grade for course {course.course_code}: {course.grade}. Valid grades are {', '.join(VALID_GRADES)}.",
                )
            if course.credits not in VALID_CREDITS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid credits for course {course.course_code}: {course.credits}. Credits must be one of {', '.join(map(str, VALID_CREDITS))}.",
                )

            # Update or insert the course
            cursor.execute(
                """
                MERGE INTO USER_COURSES AS target
                USING (SELECT %s AS user_id, %s AS course_code, %s AS course_name, %s AS grade, %s AS credits) AS source
                ON target.user_id = source.user_id AND target.course_code = source.course_code
                WHEN MATCHED THEN
                    UPDATE SET course_name = source.course_name, grade = source.grade, credits = source.credits
                WHEN NOT MATCHED THEN
                    INSERT (user_id, course_code, course_name, grade, credits)
                    VALUES (source.user_id, source.course_code, source.course_name, source.grade, source.credits);
                """,
                (user_id, course.course_code, course.course_name, course.grade, course.credits),
            )

        conn.commit()
        return {"message": "Courses updated successfully."}

    except HTTPException as e:
        conn.rollback()
        raise e  # Reraise HTTP exceptions with specific validation messages
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update courses: {str(e)}")
    finally:
        cursor.close()
        conn.close()
