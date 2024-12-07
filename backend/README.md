# Backend README

The backend of the **NEU-SAC** platform is a FastAPI-based application that serves as the backbone for handling user authentication, query processing using multi-agent architecture, transcript management, creating eligibility table. It integrates with various agents, routers, and utilities to provide a seamless API for the frontend and other system components.

## How to Run the Backend

### Prerequisites
1. **Python 3.11**: Ensure you have Python 3.11 installed.
2. **Poetry**: Install Poetry for dependency management.
3. **Environment Variables**: Ensure a `.env` file is present with the necessary keys (check below).
```
AWS_ACCESS_KEY_ID='<YOUR_AWS_ACCESS_KEY>'
AWS_SECRET_ACCESS_KEY='<YOUR_AWS_SECRET_KEY>'
AWS_REGION='<YOUR_AWS_REGION>'
S3_BUCKET_NAME='<YOUR_S3_BUCKET>'

SNOWFLAKE_ACCOUNT='<YOUR_SNOWFLAKE_ACCOUNT>'
SNOWFLAKE_USER='<YOUR_SNOWFLAKE_USER>'
SNOWFLAKE_PASSWORD='<YOUR_SNOWFLAKE_PASSWORD>'
SNOWFLAKE_ROLE='<YOUR_SNOWFLAKE_ROLE>'

NVIDIA_API_KEY='<YOUR_NVIDIA_API_KEY>'
PINECONE_API_KEY='<YOUR_PINECONE_API_KEY>'

OPENAI_API_KEY='<YOUR_OPENAI_API_KEY>'
TAVILY_API_KEY='<YOUR_TAVILY_API_KEY>'
```

### Steps to Run

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Run the backend**:
   ```bash
   poetry run backend
   ```

4. **Access the API**:
   - The backend will be available at `http://localhost:8000` by default.

## API Overview

- **Root Endpoint**: Health check for the API.
- **Authentication**: Handles user login and token management.
- **User Management**: Manages user profiles and course updation operations.
- **Transcript Processing**: Processes uploaded transcripts.
- **Task Detection**: Routes queries to appropriate agents for responses using invocations in the compiled task detection graph.

## Agents, Routers, and Utilities
For detailed information about the implemented agents, routers, and utility modules, see the **[neu_sa README](neu_sa/README.md)**.

- **Agents**: Handle query processing.
- **Routers**: Define API endpoints for authentication, user management, transcript processing, and task handling.
- **Utils**: Provide shared functions such as eligibility calculations.

