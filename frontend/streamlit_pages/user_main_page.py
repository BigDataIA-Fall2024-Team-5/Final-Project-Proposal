import streamlit as st
import os
from dotenv import load_dotenv
import requests
import pandas as pd

# Load environment variables
load_dotenv()
API_URL = os.getenv("BACKEND_URL")

def fetch_user_data(user_id, jwt_token):
    """
    Fetch user data from the backend API.
    
    Args:
        user_id (str): The ID of the user.
        jwt_token (str): The JWT token for authentication.
    
    Returns:
        dict: The user data as JSON if the request is successful; otherwise None.
    """
    try:
        response = requests.get(
            f"{API_URL}/user/{user_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching user data: {e}")
        return None

def user_main_page():
    # Check if user is logged in
    if "jwt_token" not in st.session_state or "username" not in st.session_state:
        st.error("You are not logged in. Please log in first.")
        st.session_state["page"] = "login_page"
        st.rerun()  # Ensure page reruns to redirect
        return
    
    if "user_data" not in st.session_state:
        user_id = st.session_state.get("user_id")  # Replace with actual user_id logic
        jwt_token = st.session_state.get("jwt_token")
        user_data = fetch_user_data(user_id, jwt_token)
        if user_data:
            st.session_state["user_data"] = user_data
        else:
            st.session_state["user_data"] = {}

    # Extract courses from user data
    user_courses = st.session_state["user_data"].get("courses", [])

    # Initialize session state variables for courses
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


    # Initialize session state variables if not present
    if "history" not in st.session_state:
        # Add initial bot message
        st.session_state["history"] = [{"role": "assistant", "content": "Ask me anything about your courses or general queries!"}]
    if "chat_input" not in st.session_state:
        st.session_state["chat_input"] = ""

    # Callback function to handle user input
    def handle_user_input():
        user_input = st.session_state["chat_input"].strip()
        if user_input:
            # Add user message to chat history
            st.session_state['history'].append({"role": "user", "content": user_input})

            try:
                # Get the last 5 messages in the chat history
                history = st.session_state["history"][-4:]

                # Call the FastAPI endpoint using the API_URL from .env
                response = requests.post(
                    f"{API_URL}/chat/query", 
                    headers={"Authorization": f"Bearer {st.session_state['jwt_token']}"},
                    json={"query": user_input, "history": history},
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    assistant_reply = result.get("final_response", "No response from server.")
                else:
                    assistant_reply = f"Error: {response.status_code}, {response.text}"

            except requests.exceptions.RequestException as e:
                assistant_reply = f"Error connecting to server: {str(e)}"

            # Add assistant message to chat history
            st.session_state['history'].append({"role": "assistant", "content": assistant_reply})

            # Clear input box by resetting session state
            st.session_state["chat_input"] = ""

    # Header with username display
    st.markdown(
        f"""
        <div style='display: flex; justify-content: flex-end; align-items: center;'>
            <span style='font-size: 1.2em;'>Hi, {st.session_state['username']}</span>
        </div>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    # Page layout with two columns
    col1, col2 = st.columns([3, 2.5])

    # Left Column: Dashboard
    with col1:
        #st.subheader("My Dashboard")
        #st.write("Explore your course suggestions and academic details here.")

        # Display user courses
        st.subheader("My Courses")
        if st.session_state.courses:
            courses_df = pd.DataFrame(st.session_state.courses)
            st.table(courses_df)  # Display courses as a table
        else:
            st.info("No courses added yet. Add your first course below!")

        # Buttons for user actions
    if st.button("Update Details"):
        # Clear the 'courses' session state
        variables_to_delete = ["courses","profile","user_data"]
        for var in variables_to_delete:
            if var in st.session_state:
                del st.session_state[var]

        # Navigate to the update details page
        st.session_state["page"] = "update_details_page"
        st.rerun()

    if st.button("Logout"):
        st.session_state.clear()
        st.session_state["page"] = "login_page"
        st.rerun()


    # Right Column: Chatbot Interface
    with col2:
        # Chatbot Interface heading with Clear Chat button on the same line
        chatbot_col1, chatbot_col2 = st.columns([4, 1])
        with chatbot_col1:
            st.subheader("Chatbot Interface")
        with chatbot_col2:
            if st.button("Clear Chat"):
                st.session_state["history"] = [
                    {"role": "assistant", "content": "Ask me anything about your courses or general queries!"}
                ]
                st.rerun()

        # Chat messages container with fixed height
        with st.container(height=475):  # Adjust height as needed
            for message in st.session_state['history']:
                with st.chat_message(message["role"]):
                    st.markdown(f"{message['content']}")

        # Chat input box with callback and placeholder
        st.text_input(
            "Enter your query here...",
            key="chat_input",
            placeholder="Enter your query here...",
            on_change=handle_user_input,
            label_visibility="collapsed"
        )

