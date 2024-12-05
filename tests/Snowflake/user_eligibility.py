import os
import snowflake.connector
import re

import re
import snowflake.connector

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
    )

# Fetch program requirements
def fetch_program_requirements(conn, program_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM PROGRAM_REQUIREMENTS WHERE PROGRAM_ID = %s;
        """,
        (program_id,)
    )
    result = cursor.fetchone()
    return {
        "program_id": result[0],
        "program_name": result[1],
        "max_credit_hours": result[2],
        "min_gpa": result[3],
        "core_credit_req": result[4],
        "core_options_credit_req": result[5],
        "elective_credit_req": result[6],
        "subject_credit_req": result[7],
        "elective_exceptions": result[8].split(",") if result[7] else [],
    }

def fetch_core_requirements(conn, program_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT cr.COURSE_CODE, cc.CREDITS
        FROM CORE_REQUIREMENTS cr
        JOIN COURSE_CATALOG cc ON cr.COURSE_CODE = cc.COURSE_CODE
        WHERE cr.PROGRAM_ID = %s;
        """,
        (program_id,)
    )
    return [{"course_code": row[0], "credits": row[1]} for row in cursor.fetchall()]

def fetch_core_option_courses(conn, program_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT co.COURSE_CODE, cc.CREDITS
        FROM CORE_OPTIONS_REQUIREMENTS co
        JOIN COURSE_CATALOG cc ON co.COURSE_CODE = cc.COURSE_CODE
        WHERE co.PROGRAM_ID = %s;
        """,
        (program_id,)
    )
    return [{"course_code": row[0], "credits": row[1]} for row in cursor.fetchall()]

def fetch_subject_area_requirements(conn, program_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT SUBJECT_CODE, MIN_CREDIT_HOURS
        FROM SUBJECT_AREAS
        WHERE PROGRAM_ID = %s;
        """,
        (program_id,)
    )
    # Return as a dictionary
    return {row[0]: row[1] for row in cursor.fetchall()}

# Fetch elective requirements
def fetch_elective_courses(conn, program_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT SUBJECT_CODE
        FROM ELECTIVE_REQUIREMENTS
        WHERE PROGRAM_ID = %s;
        """,
        (program_id,)
    )
    return {row[0] for row in cursor.fetchall()}

# Fetch prerequisites
def fetch_prerequisites(conn, course_code):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT PREREQUISITES
        FROM COURSE_CATALOG
        WHERE COURSE_CODE = %s;
        """,
        (course_code,)
    )
    result = cursor.fetchone()
    return result[0].strip() if result and result[0] else None

# Parse prerequisites
def parse_prerequisites(prerequisite_text):
    if not prerequisite_text:
        return []

    # Regex to match course codes with optional grade requirements
    pattern = r"([A-Z]{4} \d{4})(?: with a minimum grade of ([A-Z][-]?))?"
    matches = re.findall(pattern, prerequisite_text)

    return [
        {"course_code": match[0], "min_grade": match[1] if match[1] else None}
        for match in matches
    ]


# Grade precedence map for proper comparison
GRADE_PRECEDENCE = {
    "A+": 1, "A": 2, "A-": 3,
    "B+": 4, "B": 5, "B-": 6,
    "C+": 7, "C": 8, "C-": 9,
    "D+": 10, "D": 11, "D-": 12,
    "F": 13,
    "S": 14,  # Satisfactory
    "IP (In Progress)": 15  # In Progress (highest precedence since incomplete)
}

# Function to compare grades based on academic precedence
def compare_grades(user_grade, min_grade):
    """
    Compares user grades with the required minimum grade using precedence rules.

    :param user_grade: Grade achieved by the user (e.g., "A", "B+", "IP (In Progress)").
    :param min_grade: Minimum grade required (e.g., "B").
    :return: True if the user's grade meets or exceeds the minimum requirement, otherwise False.
    """
    user_grade_rank = GRADE_PRECEDENCE.get(user_grade)
    min_grade_rank = GRADE_PRECEDENCE.get(min_grade)

    if user_grade_rank is None or min_grade_rank is None:
        raise ValueError(f"Invalid grade encountered: User grade={user_grade}, Minimum grade={min_grade}")

    # A lower rank number indicates a better grade
    return user_grade_rank <= min_grade_rank

# Check prerequisites
def check_prerequisites(user_courses, prerequisites):
    for prerequisite in prerequisites:
        course_code = prerequisite["course_code"]
        min_grade = prerequisite["min_grade"]

        # Check if the prerequisite course exists in the user's completed courses
        matching_courses = [
            course for course in user_courses
            if course["course_code"] == course_code
        ]
        if not matching_courses:
            return False, f"Missing prerequisite: {course_code} with a minimum grade of {min_grade}."

        user_course = matching_courses[0]
        user_grade = user_course["grade"]

        # Compare grades
        if not compare_grades(user_grade, min_grade):
            return False, f"Prerequisite {course_code} requires a minimum grade of {min_grade}. User achieved {user_grade}."

    return True, "Prerequisites satisfied."

# Fetch user data
def fetch_user_data(conn, user_id):
    cursor = conn.cursor()

    # Fetch user profile
    cursor.execute(
        """
        SELECT PROGRAM_ID, GPA FROM USER_PROFILE WHERE USER_ID = %s;
        """,
        (user_id,)
    )
    profile = cursor.fetchone()
    if not profile:
        raise ValueError(f"No user profile found for user_id: {user_id}")

    program_id, gpa = profile

    # Handle null GPA
    if gpa is None:
        gpa = 0.0

    # Fetch completed courses
    cursor.execute(
        """
        SELECT COURSE_CODE, CREDITS, GRADE
        FROM USER_COURSES
        WHERE USER_ID = %s;
        """,
        (user_id,)
    )
    courses = cursor.fetchall()
    completed_courses = [
        {"course_code": row[0], "credits": row[1], "grade": row[2]} for row in courses
    ]

    return {"program_id": program_id, "gpa": gpa, "completed_courses": completed_courses}

# Clear user eligibility
def clear_user_eligibility(conn, user_id):
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM USER_ELIGIBILITY WHERE USER_ID = %s;
        """,
        (user_id,)
    )
    conn.commit()

# Insert into eligibility
def insert_into_eligibility(conn, user_id, code, eligible, reason, status):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO USER_ELIGIBILITY (USER_ID, COURSE_OR_REQUIREMENT, ELIGIBLE, DETAILS, STATUS)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (user_id, code, eligible, reason, status),
    )
    conn.commit()


# Main eligibility recalculation function
def recalculate_eligibility(user_id):
    conn = get_snowflake_connection()
    try:
        # Fetch user and program data
        print(f"Fetching data for user_id: {user_id}")
        user_data = fetch_user_data(conn, user_id)
        program_requirements = fetch_program_requirements(conn, user_data["program_id"])
        core_courses = fetch_core_requirements(conn, user_data["program_id"])
        core_option_courses = fetch_core_option_courses(conn, user_data["program_id"])
        subject_area_requirements = fetch_subject_area_requirements(conn, user_data["program_id"])
        elective_subjects = fetch_elective_courses(conn, user_data["program_id"])  # Valid elective subjects

        print("Fetched all required data for eligibility calculation.")

        # Clear existing eligibility data
        print(f"Clearing existing eligibility data for user_id: {user_id}")
        clear_user_eligibility(conn, user_id)
        print("Cleared existing eligibility data.")

        # ---- Process Core Requirements ----
        print("Processing core requirements...")

        # Track completed core credits
        completed_core_credits = 0
        processed_courses = set()  # Tracks courses processed for core, core options, and electives

        for core_course in core_courses:
            course_code = core_course["course_code"]

            if course_code in processed_courses:
                continue  # Skip already processed courses
            processed_courses.add(course_code)

            print(f"Processing Core Course: {course_code}")

            # Check if the user has completed this course
            matching_courses = [
                c for c in user_data["completed_courses"] if c["course_code"] == course_code
            ]
            if matching_courses:
                user_course = matching_courses[0]
                grade = user_course["grade"]

                if grade == "F":
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Failed with grade '{grade}'. (Category: Core Requirement)", "CALCULATED"
                    )
                    continue

                if grade == "IP (In Progress)":
                    # Add in-progress credits to the completed credits
                    completed_core_credits += core_course["credits"]
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"In progress with grade '{grade}'. (Category: Core Requirement)", "PENDING"
                    )
                    continue

                # Add completed credits
                completed_core_credits += core_course["credits"]
                insert_into_eligibility(
                    conn, user_id, course_code, False,
                    f"Already completed with grade '{grade}'. (Category: Core Requirement)", "CALCULATED"
                )
            else:
                # Check prerequisites for the course
                prerequisites_text = fetch_prerequisites(conn, course_code)
                if prerequisites_text:
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Have not started/completed Prerequisites: {prerequisites_text}. (Category: Core Requirement)", "CALCULATED"
                    )
                else:
                    # No prerequisites, mark the course as available
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        "Have not started/completed it has no prerequisites. (Category: Core Requirement)", "CALCULATED"
                    )

        print(f"Completed core credits: {completed_core_credits}/{program_requirements['core_credit_req']}.")


        # ---- Process Core Options Requirements ----
        print("Processing core options requirements...")

        # Track completed core option credits
        completed_core_option_credits = 0
        core_options_as_electives = set()  # Track courses counted as electives after core options satisfied

        for course in core_option_courses:
            course_code = course["course_code"]

            
            if course_code in processed_courses:
                continue  # Skip already processed courses
            processed_courses.add(course_code)

            print(f"Processing Core Option Course: {course_code}")

            # Check if user has completed this course
            matching_courses = [
                c for c in user_data["completed_courses"] if c["course_code"] == course_code
            ]
            if matching_courses:
                user_course = matching_courses[0]
                grade = user_course["grade"]

                if grade == "F":
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Failed with grade '{grade}'. (Category: Core Options)", "CALCULATED"
                    )
                    continue

                if grade == "IP (In Progress)":
                    # Add in-progress credits to the completed credits
                    completed_core_option_credits += course["credits"]
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"In progress with grade '{grade}'. (Category: Core Options)", "PENDING"
                    )
                    continue

                # Add credits toward core options
                if completed_core_option_credits < program_requirements["core_options_credit_req"]:
                    completed_core_option_credits += course["credits"]
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"Already completed with grade '{grade}'. Counted toward core options. (Category: Core Options)",
                        "CALCULATED"
                    )
                else:
                    # Core options requirement already satisfied
                    subject_code = course_code[:4]
                    if subject_code in elective_subjects:
                        core_options_as_electives.add(course_code)  # Mark as counted toward electives
                        insert_into_eligibility(
                            conn, user_id, course_code, True,
                            f"This was one of Core options requirement but as it is already satified it can be counted as part of program electives under {subject_code}.",
                            "CALCULATED"
                        )
                    else:
                        insert_into_eligibility(
                            conn, user_id, course_code, False,
                            f"Core options requirement already satisfied. (Category: Core Options)",
                            "CALCULATED"
                        )
            else:
                # Check prerequisites for the course
                prerequisites_text = fetch_prerequisites(conn, course_code)
                if prerequisites_text:
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Have not started/completed Prerequisites: {prerequisites_text}. (Category: Core Options)", "CALCULATED"
                    )
                else:
                    # No prerequisites, mark as available to take
                    if completed_core_option_credits < program_requirements["core_options_credit_req"]:
                        insert_into_eligibility(
                            conn, user_id, course_code, True,
                            "Have not started/completed. It has no prerequisites. Available to take as part of (Category: Core Options).", "CALCULATED"
                        )
                    else:
                        # After core options satisfied, check if it can be elective
                        subject_code = course_code[:4]
                        if subject_code in elective_subjects:
                            core_options_as_electives.add(course_code)  # Mark as counted toward electives
                            insert_into_eligibility(
                                conn, user_id, course_code, True,
                                "Core options requirement already satisfied but can be taken as an elective. (Category: Core Options and Elective)",
                                "CALCULATED"
                            )
                        else:
                            insert_into_eligibility(
                                conn, user_id, course_code, True,
                                "Core options requirement already satisfied. (Category: Core Options)",
                                "CALCULATED"
                            )

        print(f"Completed core option credits: {completed_core_option_credits}/{program_requirements['core_options_credit_req']}.")



        # ---- Process Subject Area and Program Electives ----
        print("Processing subject area and program electives...")

        # Track accumulated credits for each subject code
        subject_credits = {subject_code: 0 for subject_code in subject_area_requirements.keys()}
        subject_area_courses = {subject_code: [] for subject_code in subject_area_requirements.keys()}  # Track courses for each subject
        program_elective_credits = 0  # Track total elective credits across all subjects
        elective_courses = []  # Track courses contributing to electives

        # Fetch elective exceptions from program requirements
        elective_exceptions = program_requirements.get("elective_exceptions", [])

        def consolidate_requirements(completed, required, courses, category, electives=None, exceptions=None):
            course_list = ", ".join(courses)
            additional_info = ""
            if electives:
                additional_info += f" Electives are subject code with ({', '.join(electives)})."
            if exceptions:
                additional_info += f" Exceptions are ({', '.join(exceptions)})."
            return (
                f"{completed}/{required} credits completed for {category} requirements. "
                f"Which are ({course_list})." + additional_info
            )

        # Step 1: Process completed courses
        for course in user_data["completed_courses"]:
            course_code = course["course_code"]
            subject_code = course_code[:4]  # Extract subject prefix (e.g., INFO, CSYE)

            # Skip courses already processed in core requirements or core options
            if course_code in processed_courses and course_code not in core_options_as_electives:
                print(f"Skipping already processed course: {course_code}")
                continue

            print(f"Processing course_code: '{course_code}'")

            # If this course was counted as a core option elective, handle it
            if course_code in core_options_as_electives:
                print(f"Processing core option course counted as elective: {course_code}")
                program_elective_credits += course["credits"]  # Add to total elective credits
                elective_courses.append(course_code)
                insert_into_eligibility(
                    conn, user_id, course_code, False,
                    f"Already completed with grade '{course['grade']}'. (Core option course counted as elective)",
                    "CALCULATED"
                )
                continue  # Skip further processing for this course

            # Check if course counts for a specific subject area
            if subject_code in subject_area_requirements:
                required_credits = subject_area_requirements[subject_code]
                available_credits = min(course["credits"], required_credits - subject_credits[subject_code])

                if course["grade"] == "F":
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Failed with grade '{course['grade']}'. (Category: Subject area)",
                        "CALCULATED"
                    )
                    continue

                if course["grade"] == "IP (In Progress)":
                    # Add in-progress credits to the completed credits
                    subject_credits[subject_code] += available_credits
                    subject_area_courses[subject_code].append(course_code)
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"In progress with grade '{course['grade']}'. (Category: Subject area)",
                        "PENDING"
                    )
                    continue

                if available_credits > 0:
                    # Allocate credits toward the specific subject area
                    subject_credits[subject_code] += available_credits
                    subject_area_courses[subject_code].append(course_code)
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"Already completed with grade '{course['grade']}'. (Category: Subject area)",
                        "CALCULATED"
                    )

                # Handle excess credits as electives
                excess_credits = course["credits"] - available_credits
                if excess_credits > 0:
                    program_elective_credits += excess_credits
                    elective_courses.append(course_code)
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"Already completed with grade '{course['grade']}'. (Category: Program elective)",
                        "CALCULATED"
                    )
                processed_courses.add(course_code)
                continue  # Skip further processing for this course

            # Check if course counts for program electives
            if subject_code in elective_subjects:
                if course["grade"] == "F":
                    insert_into_eligibility(
                        conn, user_id, course_code, True,
                        f"Failed with grade '{course['grade']}'. (Category: Program elective)",
                        "CALCULATED"
                    )
                    continue

                if course["grade"] == "IP (In Progress)":
                    # Add in-progress credits to the completed credits
                    program_elective_credits += course["credits"]
                    elective_courses.append(course_code)
                    insert_into_eligibility(
                        conn, user_id, course_code, False,
                        f"In progress with grade '{course['grade']}'. (Category: Program elective)",
                        "PENDING"
                    )
                    continue

                program_elective_credits += course["credits"]
                elective_courses.append(course_code)
                insert_into_eligibility(
                    conn, user_id, course_code, False,
                    f"Already completed with grade '{course['grade']}'. (Category: Program elective)",
                    "CALCULATED"
                )
                processed_courses.add(course_code)
                continue

        # Step 2: Summarize subject area requirements
        for subject_code, required_credits in subject_area_requirements.items():
            completed_credits = subject_credits[subject_code]
            courses = subject_area_courses[subject_code]
            subject_area_status = consolidate_requirements(
                completed_credits, required_credits, courses, f"subject area ({subject_code})"
            )
            insert_into_eligibility(
                conn, user_id, f"SUBJECT_AREA_{subject_code}", completed_credits < required_credits,
                subject_area_status, "CALCULATED"
            )

        # Step 3: Summarize elective requirements
        elective_credit_req = program_requirements["elective_credit_req"]  # Total required elective credits
        elective_status = consolidate_requirements(
            program_elective_credits, elective_credit_req, elective_courses, "elective",
            electives=elective_subjects, exceptions=elective_exceptions
        )
        insert_into_eligibility(
            conn, user_id, "ELECTIVES", program_elective_credits < elective_credit_req,
            elective_status, "CALCULATED"
        )

        print("Subject area and program elective requirements processing completed.")



    except Exception as e:
            print(f"Error during eligibility recalculation: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    user_id = 101  # Replace with the user ID you want to test
    recalculate_eligibility(user_id)
