import streamlit as st
from streamlit_pages.login_page import login_page
from streamlit_pages.register_page import register_page
from streamlit_pages.user_main_page import user_main_page
from streamlit_pages.update_details_page import update_details_page

# Set the page layout to wide mode
st.set_page_config(page_title="NEU-SA", page_icon="📚", layout="wide")  # This must be the first Streamlit command

# Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state["page"] = "login_page"  # Default page is the login page

# Define a function to handle navigation
def navigate_to(page_name):
    st.session_state["page"] = page_name
    st.rerun()  # Trigger rerun to navigate to the new page
    
# Display session state for debugging
st.sidebar.header("Debugging Info")
st.sidebar.write("Session State:")
st.sidebar.write(st.session_state)

# Navigation logic with a fallback
if st.session_state["page"] == "login_page":
    login_page()
elif st.session_state["page"] == "register_page":
    register_page()
elif st.session_state["page"] == "user_main_page":
    user_main_page()
elif st.session_state["page"] == "update_details_page":
    update_details_page()
else:
    st.error("Page not found. Redirecting to login.")
    navigate_to("login_page")
