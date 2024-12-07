import streamlit as st

def expiration_page():
    """
    Display an expiration message and prompt the user to log in again.
    """
    # Page title and message
    st.title("Session Expired")
    st.warning("Your session has expired. Please log in again to continue.")

    # Redirect to login page button
    if st.button("Go to Login Page"):
        st.session_state["page"] = "login_page"
        st.session_state.clear()
        st.rerun()
