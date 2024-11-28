import streamlit as st
import requests
import os
from dotenv import load_dotenv
from PIL import Image
import base64

# Load environment variables
load_dotenv()
API_URL = os.getenv("BACKEND_URL")

def login_page():
    st.title("Northeastern University Student Assistance Chatbot")
    st.markdown("---")

    # Load logo
    logo_path = "logo.png"  # Update this path to your actual logo file
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            logo_data = base64.b64encode(img_file.read()).decode()

    # CSS for styling the left-hand image
    st.markdown(
        f"""
        <style>
        .logo-container {{
            text-align: center;
            margin-top: 20px;
        }}
        .rounded-logo {{
            border-radius: 15px; /* Round the corners */
            width: 80%; /* Set the width to 80% */
            height: auto; /* Maintain aspect ratio */
            margin: 0 auto; /* Center align the image */
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Create two columns for split layout
    col1, col2 = st.columns([1, 2])  # Adjust column widths as needed

    # Left Column: Logo
    with col1:
        if os.path.exists(logo_path):
            st.markdown(
                f"""
                <div class="logo-container">
                    <img src="data:image/png;base64,{logo_data}" class="rounded-logo" alt="Logo">
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.error("Logo not found!")

    # Right Column: Login Form
    with col2:
        st.subheader("Login to Continue")
        st.write("Plan your courses and get instant answers to your queries with our intelligent chatbot!")
        
        # Input fields
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        # Login button
        if st.button("Login"):
            # Validate input fields
            if not username or not password:
                st.error("Both fields are required.")
                return

            # API call to backend
            try:
                response = requests.post(f"{API_URL}/auth/login", json={"username": username, "password": password})
                if response.status_code == 200:
                    # Extract data from the response
                    data = response.json()

                    # Save relevant session state variables
                    st.session_state["jwt_token"] = data["access_token"]
                    st.session_state["username"] = data["username"]  # Save username
                    st.session_state["user_id"] = data["user_id"]    # Save user ID

                    # Navigate to the User Main page
                    st.session_state["page"] = "user_main_page"
                    st.success(f"Welcome back, {data['username']}!")
                    st.rerun()

                elif response.status_code == 404:
                    st.error("User not found. Please check your username.")
                elif response.status_code == 401:
                    st.error("Incorrect password. Please try again.")
                elif response.status_code == 500:
                    st.error(response.json().get("detail", "Server error. Please try again later."))
                else:
                    st.error("An unexpected error occurred. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error("Unable to connect to the server. Please check your network connection.")
            except requests.exceptions.Timeout:
                st.error("The request timed out. Please try again later.")
            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred: {e}")

        # Navigation to registration page
        if st.button("Register"):
            st.session_state["page"] = "register_page"
            st.rerun()
