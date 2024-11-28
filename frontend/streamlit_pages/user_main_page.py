import streamlit as st
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
API_URL = os.getenv("BACKEND_URL")

def user_main_page():
    # Check if user is logged in
    if "jwt_token" not in st.session_state or "username" not in st.session_state:
        st.error("You are not logged in. Please log in first.")
        st.session_state["page"] = "login_page"
        st.rerun()  # Ensure page reruns to redirect
        return

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
                # Call the FastAPI endpoint using the API_URL from .env
                response = requests.post(
                    f"{API_URL}/chat/detect_task",  # Use the dynamic API_URL here
                    json={"query": user_input},
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    assistant_reply = result.get("response", "No response from server.")
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
        st.subheader("My Dashboard")
        st.write("Explore your course suggestions and academic details here.")
        st.write("Add more details or summaries for your user dashboard.")

        # Buttons for user actions
        if st.button("Update Details"):
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

