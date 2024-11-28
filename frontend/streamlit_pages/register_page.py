import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_URL = os.getenv("BACKEND_URL")

def register_page():
    st.title("Register")
    st.write("Create a new account.")

    # Initialize session state for fields if not already present
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "password" not in st.session_state:
        st.session_state["password"] = ""
    if "confirm_password" not in st.session_state:
        st.session_state["confirm_password"] = ""
    if "registration_success" not in st.session_state:
        st.session_state["registration_success"] = False
    if "program_name" not in st.session_state:
        st.session_state["program_name"] = "Select Program Name"
    if "campus" not in st.session_state:
        st.session_state["campus"] = "Select Campus"
    if "college" not in st.session_state:
        st.session_state["college"] = "Select College"

    # Reset session state after successful registration
    if st.session_state["registration_success"]:
        st.success("Account created successfully! Please log in.")
        # Reset session fields
        st.session_state["registration_success"] = False
        st.session_state["password"] = ""
        st.session_state["confirm_password"] = ""
        st.session_state["program_name"] = "Select Program Name"  # Reset Program Name
        st.session_state["campus"] = "Select Campus"  # Reset Campus
        st.session_state["college"] = "Select College"  # Reset College

    # Input fields
    username = st.text_input("Username", placeholder="Enter your username", key="username")
    password = st.text_input("Password", type="password", placeholder="Enter your password", key="password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password", key="confirm_password")

    # Dropdown for Program Name
    program_options = [
        "Select Program Name",  # Default invalid option
        "Information Systems, MSIS",
        "Cyber-Physical Systems, MS",
        "Data Architecture and Management, MS",
        "Software Engineering Systems, MS",
        "Telecommunication Networks, MS",
    ]
    program_name = st.selectbox("Program Name", options=program_options, key="program_name")

    # Dropdown for College Selection
    college_options = ["Select College", "College of Engineering"]
    college = st.selectbox("College", options=college_options, key="college")

    # Dropdown for Campus Selection
    campus_options = [
        "Select Campus",  # Default invalid option
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
    campus = st.selectbox("Campus", options=campus_options, key="campus")

    # Register Button
    if st.button("Register"):
        # Ensure mandatory fields are filled
        if not username or not password or not confirm_password:
            st.error("All fields are required.")
            return

        # Ensure passwords match
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        # Validate dropdown selections
        if program_name == "Select Program Name":
            st.error("Please select a valid Program Name.")
            return
        if college == "Select College":
            st.error("Please select a valid College.")
            return
        if campus == "Select Campus":
            st.error("Please select a valid Campus.")
            return

        # API call to backend
        try:
            response = requests.post(f"{API_URL}/auth/register", json={
                "username": username,
                "password": password,
                "program_name": program_name,
                "college": college,
                "campus": campus,
            })
            if response.status_code == 200:
                st.session_state["registration_success"] = True  # Set flag for success
                st.rerun()  # Refresh the page to display success message
            elif response.status_code == 400:
                st.error(response.json().get("detail", "Failed to register."))
            else:
                st.error("An unexpected error occurred.")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the server: {e}")

    # Navigation back to login page
    if st.button("Back to Login"):
        # Reset session state for registration
        for key in ["username", "password", "confirm_password", "registration_success", "program_name", "campus", "college"]:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state["page"] = "login_page"  # Navigate to login page
        st.rerun()
