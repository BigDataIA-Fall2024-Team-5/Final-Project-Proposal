# Frontend README

The **NEU-SAC Frontend** is a Streamlit-based user interface for the Northeastern University Student Assistance Chatbot. This document provides setup instructions, environment configurations, and details about the core components of the application.

## Overview

The frontend offers:
- **User Authentication**: Login and registration functionality.
- **Profile Management**: Update user profile and course details.
- **Course Management**: Add, update, or delete courses.
- **Chatbot Interface**: Query NEU-SA for course-related or general university information.

## How to Run the Backend

### Prerequisites
1. **Python 3.11**: Ensure you have Python 3.11 installed (>=3.11,<3.13).
2. **Poetry**: Install Poetry for dependency management.
3. **Environment Variables**: Ensure a `.env` file is present with the necessary keys (check below).
```env
BACKEND_URL=<YOUR_BACKEND_API_URL>
```

Replace `<YOUR_BACKEND_API_URL>` with the URL of the **[backend](backend/README.md)** API.

### Steps to Run

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Run the frontend**:
   ```bash
   poetry run streamlit run app.py
   ```

4. **Access the Streamlit Application**:
   - The frontend will be available at `http://localhost:8501` by default.

## Application Structure

### [`app.py`](/frontend/app.py)
This file initializes the Streamlit app and manages page navigation.

Key Features:
- **Page Layout**: Sets up a wide layout with sidebar navigation.
- **Page Navigation**: Handles transitions between login, registration, user dashboard, and profile management pages.

## Streamlit Pages

### [`login_page.py`](/frontend/streamlit_pages/login_page.py)
Allows users to log in to the NEU-SA system.
- **Features**:
  - Username and password input fields.
  - API integration for user authentication.
  - Navigation to the registration page.

### [`register_page.py`](/frontend/streamlit_pages/register_page.py)
Enables new users to create an account.
- **Features**:
  - Username, password, and program selection inputs.
  - Dropdown menus for program, college, and campus selection.
  - Validates input fields and communicates with the backend API.

### [`user_main_page.py`](/frontend/streamlit_pages/user_main_page.py)
The main dashboard for authenticated users.
- **Features**:
  - Displays user courses in a tabular format.
  - Provides a chatbot interface for queries.
  - Navigation to the profile update page or logout.

### [`update_details_page.py`](/frontend/streamlit_pages/update_details_page.py)
Allows users to manage their profile and course details.
- **Features**:
  - Profile updates (e.g., program, college, GPA).
  - Course management: Add, delete, and save courses.
  - Transcript upload and processing.

### [`expiration_page.py`](/frontend/streamlit_pages/expiration_page.py)
Notifies users when their session has expired.
- **Features**:
  - Displays an expiration message.
  - Redirects users to the login page.
