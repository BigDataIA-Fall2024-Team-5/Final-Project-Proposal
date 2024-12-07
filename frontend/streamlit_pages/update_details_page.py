import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_URL = os.getenv("BACKEND_URL")  # Backend API URL

def handle_session_expiration():
    """
    Check response for session expiration and display the expiration page if token has expired.
    """
    st.session_state.clear()
    st.session_state["page"] = "expiration_page"
    st.rerun()

# Predefined dropdown options
COLLEGES = ["College of Engineering"]
PROGRAMS = [
    "Information Systems, MSIS",
    "Cyber-Physical Systems, MS",
    "Data Architecture and Management, MS",
    "Software Engineering Systems, MS",
    "Telecommunication Networks, MS",
    "Information Systems MSIS-Bridge",
    "Information Systems MSIS—Bridge—Online",
    "Information Systems MSIS—Online",
    "Blockchain and Smart Contract Engineering Graduate Certificate",
    "Broadband Wireless Systems Graduate Certificate",
    "IP Telephony Systems Graduate Certificate",
    "Software Engineering Systems Graduate Certificate",
]

PROGRAM_ID_MAP = {
    "Information Systems, MSIS": "MP_IS_MSIS",
    "Cyber-Physical Systems, MS": "MP_CPS_MS",
    "Data Architecture and Management, MS": "MP_DAM_MS",
    "Software Engineering Systems, MS": "MP_SES_MS",
    "Telecommunication Networks, MS": "MP_TN_MS",
    "Information Systems MSIS-Bridge": "MP_IS_MSIS_BR",
    "Information Systems MSIS—Bridge—Online": "MP_IS_MSIS_BRO",
    "Information Systems MSIS—Online": "MP_IS_MSIS_O",
    "Blockchain and Smart Contract Engineering Graduate Certificate": "MP_BC_SC_CERT",
    "Broadband Wireless Systems Graduate Certificate": "MP_BW_CERT",
    "IP Telephony Systems Graduate Certificate": "MP_IPT_CERT",
    "Software Engineering Systems Graduate Certificate": "MP_SES_CERT",
}

CAMPUS_OPTIONS = [
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

# Fetch user data
def fetch_user_data(user_id, jwt_token):
    try:
        response = requests.get(
            f"{API_URL}/user/{user_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if response.status_code == 401:
            handle_session_expiration()
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching user data: {e}")
        return None

#Fetch existing transcript link from the backend and generate presigned URL
def fetch_transcript_link(user_id, jwt_token):
    try:
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = requests.get(f"{API_URL}/transcripts/transcript_link/{user_id}", headers=headers)

        if response.status_code == 200:
            return response.json().get("transcript_presigned_url")
        elif response.status_code == 401:
                handle_session_expiration()
        elif response.status_code == 404:
            return None  # No transcript found
        else:
            st.error("Failed to fetch transcript link.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching transcript link: {e}")
        return None


# Function to upload transcript
def upload_transcript(file, user_id, jwt_token):
    # Validate file size
    if file.size > 5 * 1024 * 1024:  # 5MB in bytes
        st.error("The uploaded file exceeds the maximum size of 5MB. Please upload a smaller file.")
        return None

    try:
        # Prepare headers and payload
        headers = {"Authorization": f"Bearer {jwt_token}"}
        files = {"file": file}
        data = {"user_id": user_id}

        # Make the POST request to the backend
        response = requests.post(
            f"{API_URL}/transcripts/upload_transcript",
            files=files,
            data=data,
            headers=headers,
        )
        if response.status_code == 401:
            handle_session_expiration()
        # Handle response status
        elif response.status_code != 200:
            st.error(f"Failed to upload transcript: {response.json().get('detail', 'Unknown error occurred.')}")
            return None

        # Parse and return response data
        return response.json()

    except requests.exceptions.RequestException as e:
        # Handle exceptions during the request
        st.error(f"Error uploading transcript: {e}")
        return None

def save_courses_to_snowflake(user_id, courses, jwt_token):
    try:
        response = requests.put(
            f"{API_URL}/user/{user_id}/courses",
            json=courses,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if response.status_code == 401:
            handle_session_expiration()

        # Raise an exception for HTTP error responses
        response.raise_for_status()

        # Success message
        st.success("Courses updated successfully!")

        if "completed_credits" in response.json():
            st.session_state["completed_credits"] = response.json()["completed_credits"]

        return response.json()

    except requests.exceptions.HTTPError as e:
        # Parse backend error message
        if response.status_code == 401:
            handle_session_expiration()
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "Unknown error occurred.")
            st.session_state["save_courses_error"] = error_detail  # Store detailed error in session state
            st.error(f"Error saving courses: {error_detail}")
        else:
            st.session_state["save_courses_error"] = f"HTTP error occurred: {e}"  # General HTTP error
            st.error(f"Error saving courses: {e}")
        return None

    except requests.exceptions.RequestException as e:
        # Handle generic request exceptions
        st.session_state["save_courses_error"] = f"Request exception: {e}"  # Store detailed error in session state
        st.error(f"Error saving courses: {e}")
        return None

# Function to save user profile
def save_profile_to_snowflake(user_id, user_profile, jwt_token):
    try:
        response = requests.put(
            f"{API_URL}/user/{user_id}/profile",
            json=user_profile,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        if response.status_code == 401:
            handle_session_expiration()
        response.raise_for_status()
        st.success("Profile updated successfully!")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saving profile: {e}")
        return None

# Page layout
def update_details_page():
    st.title("Manage Your Profile and Courses")

    if st.button("Back to Main Page"):
        variables_to_delete = ["courses", "transcript_presigned_url", "selected_course_to_delete","additional_details","courses_detected","user_profile","message","save_courses_error","user_data","courses"]
        for var in variables_to_delete:
            if var in st.session_state:
                del st.session_state[var]

        st.session_state["page"] = "user_main_page"
        st.rerun()

    if "jwt_token" not in st.session_state or "user_id" not in st.session_state:
        st.error("You are not logged in. Please log in first.")
        st.session_state["page"] = "login_page"
        st.rerun()
        return

    user_id = st.session_state["user_id"]
    jwt_token = st.session_state["jwt_token"]

    # Fetch user data
    user_data = fetch_user_data(user_id, jwt_token)
    if not user_data:
        return

    user_profile = user_data.get("profile", {})
    user_courses = user_data.get("courses", [])
    uploaded_transcript_url = st.session_state.get("transcript_presigned_url", "")

    # User Profile Section (Top of the Page, Split into Two Columns)
    st.subheader("User Profile")
    profile_col1, profile_col2 = st.columns([1, 1])

    # Left Column: College, Program Name, Program ID
    with profile_col1:
        college = st.selectbox("College", COLLEGES, index=COLLEGES.index(user_profile.get("college", "College of Engineering")))
        program_name = st.selectbox("Program Name", PROGRAMS, index=PROGRAMS.index(user_profile.get("program_name", PROGRAMS[0])))
        st.caption("After updating program, make sure to save your courses.")
        program_id = PROGRAM_ID_MAP.get(program_name, "Not Provided")
        st.text_input("Program ID", program_id, disabled=True)

    # Right Column: Campus and GPA
    with profile_col2:
        campus = st.selectbox("Campus", CAMPUS_OPTIONS, index=CAMPUS_OPTIONS.index(user_profile.get("campus", CAMPUS_OPTIONS[0])))
        gpa = st.number_input("GPA", value=min(user_profile.get("gpa", 0.0), 4.0), min_value=0.0, max_value=4.0, format="%.2f")
        completed_credits = st.session_state.get("completed_credits", user_profile.get("completed_credits", 0))
        st.text_input("Completed Credits", value=completed_credits, disabled=True)

    if st.button("Save Profile"):
        updated_profile = {
            "college": college,
            "program_name": program_name,
            "program_id": program_id,
            "gpa": gpa,
            "campus": campus
        }
        save_profile_to_snowflake(user_id, updated_profile, jwt_token)
        st.success("Profile updated successfully!")

    st.markdown("---")

    # Split Layout: "My Courses" and "Transcript Preview"
    col1, col2 = st.columns([1, 1])

    # "My Courses" on the Left
    with col1:
        st.subheader("My Courses")

        if "courses" not in st.session_state:
            st.session_state.courses = user_courses

        # Standardize course keys
        standardized_courses = []
        for course in st.session_state.courses:
            standardized_course = {
                "course_code": course.get("course_code"),
                "course_name": course.get("course_name"),
                "grade": course.get("grade"),
                "credits": course.get("credits"),
            }
            standardized_courses.append(standardized_course)
        st.session_state.courses = standardized_courses

        if st.session_state.courses:
            courses_df = pd.DataFrame(st.session_state.courses)
            st.table(courses_df)
        else:
            st.info("No courses added yet. Add your first course below!")

    # Transcript Preview on the Right
    with col2:
        st.subheader("Auto Detect")

        # Fetch transcript link from the backend when the page loads
        if "transcript_presigned_url" not in st.session_state:
            st.session_state["transcript_presigned_url"] = fetch_transcript_link(user_id, jwt_token)

        # Display the transcript link if it exists
        if st.session_state["transcript_presigned_url"]:
            st.markdown("Note: Please ensure that the transcript is up to date and accurate.")

        # Message when no transcript is uploaded
        else:
            st.info("No transcript uploaded yet. Please upload one below.")

        # Drag-and-drop file uploader and Upload button in the same row
        row_col1, row_col2 = st.columns([3, 0.75])
        with row_col1:
            uploaded_file = st.file_uploader("Choose a transcript file (PDF only)", type=["pdf"])
        with row_col2:
            upload_button = st.button("Click to Process Transcript")

        # Handle upload logic
        if upload_button and uploaded_file:
            # Call the upload_transcript function
            result = upload_transcript(uploaded_file, user_id, jwt_token)

            if result:
                # Success: Process the response
                st.success("Transcript uploaded successfully!")

                # Store transcript information in session state
                st.session_state["transcript_presigned_url"] = result.get("transcript_presigned_url")
                st.session_state["courses"] = result.get("courses", [])
                st.session_state["additional_details"] = result.get("additional_details", {})

                # Trigger a page refresh
                st.rerun()

            else:
                # Error handling
                st.error("Failed to upload and process the transcript.")
        elif upload_button and not uploaded_file:
            st.error("Please upload a valid PDF file.")

        # After rerun, display the transcript information and additional details
        if "transcript_presigned_url" in st.session_state:
            st.markdown(f"Uploaded Transcript: [View PDF]({st.session_state['transcript_presigned_url']})")

        if "additional_details" in st.session_state:
            additional_details = st.session_state["additional_details"]
            user_profile = additional_details.get("user_profile", {})
            details_text = f"**Courses Detected:** {additional_details.get('courses_detected', 0)}\n\n"
            for key, value in user_profile.items():
                details_text += f"**{key.replace('_', ' ').capitalize()}:** {value}\n"

            # Display additional details in a text box
            st.text_area("Details from Extraction", details_text, height=75, disabled=True)


    st.write("")
    st.write("")
    st.write("")
    # Split Layout: "Add a New Course" and "Delete a Course"
    col3, col4 = st.columns([1, 1])

    # "Add a New Course" on the Left
    import re  # Import the regular expression module

    with col3:
        st.subheader("Add a New Course")
        with st.form(key="course_form"):
            # First Row: Course Code and Course Name
            row1_col1, row1_col2 = st.columns([1, 2])
            with row1_col1:
                course_code = st.text_input("Course Code")
            with row1_col2:
                course_name = st.text_input("Course Name")

            # Second Row: Grade and Credits
            row2_col1, row2_col2 = st.columns([1, 1])
            with row2_col1:
                grade = st.selectbox("Grade", ['Select Grade', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'F', 'IP (In Progress)'])
            with row2_col2:
                credits = st.selectbox("Credits", ['Select Credits', 0,1, 2, 3, 4])

            # Submit Button
            submit_button = st.form_submit_button(label="Add Course")

            if submit_button:
                # Validate course code format
                if not re.match(r'^[A-Z]{4} \d{4}$', course_code):
                    st.error("Invalid course code format. It should be in the format 'INFO 5100'.")
                elif not course_name:
                    st.error("Please provide the Course Name.")
                elif grade == "Select Grade":
                    st.error("Please select a valid Grade for the course.")
                elif credits == "Select Credits":
                    st.error("Please select valid Credits for the course.")
                else:
                    # Check for duplicates
                    if not any(course["course_code"] == course_code for course in st.session_state.courses):
                        # Add the course to session state
                        st.session_state.courses.append({
                            "course_code": course_code,
                            "course_name": course_name,
                            "grade": grade,
                            "credits": credits,
                        })
                        st.success(f"Course {course_code} - {course_name} added successfully!")
                        st.rerun()  # Refresh the page
                    else:
                        st.error(f"Course {course_code} already exists.")  # Duplicate found


    # "Delete a Course" on the Right
    with col4:
        st.subheader("Delete a Course")
        with st.form(key="delete_course_form"):
            if "selected_course_to_delete" not in st.session_state:
                st.session_state.selected_course_to_delete = None

            if st.session_state.courses:
                selected_course = st.selectbox(
                    "Select a course to delete",
                    [course["course_code"] for course in st.session_state.courses],
                    key="delete_course_select"
                )
                st.session_state.selected_course_to_delete = selected_course

                delete_button = st.form_submit_button(label="Delete Selected Course")

                if delete_button:
                    st.session_state.courses = [
                        course for course in st.session_state.courses
                        if course["course_code"] != st.session_state.selected_course_to_delete
                    ]
                    st.success(f"Course {st.session_state.selected_course_to_delete} deleted successfully!")

                    # Save updated courses to backend
                    save_courses_to_snowflake(user_id, st.session_state.courses, jwt_token)
                    st.rerun()

    # Save Courses Button
    if st.button("Save 'My Course' Changes"):
        result = save_courses_to_snowflake(user_id, st.session_state.courses, jwt_token)
        
        if result:  # If the response indicates success
            st.session_state["message"] = {"type": "success", "text": "My Courses Updated Successfully!"}
            st.rerun()  # Trigger rerun only on success
        else:
            # Capture detailed error message from save_courses_to_snowflake
            detailed_error = st.session_state.get("save_courses_error", "Failed to update courses.")
            st.session_state["message"] = {"type": "error", "text": detailed_error}
            st.rerun()  # Trigger rerun even on failure to persist the error


    # Display persistent messages after rerun
    if "message" in st.session_state:
        message = st.session_state.pop("message")  # Remove the message after displaying it
        if message["type"] == "success":
            st.success(message["text"])
        elif message["type"] == "error":
            st.error(message["text"])  # Display the error message



