# neu_sa README

The **neu_sa** is a core component of the NEU-SAC platform, responsible for orchestrating backend functionalities such as user authentication, task routing, eligibility calculations, transcript management, and information retrieval. This README provides an overview of its architecture and components.

## Overview

The **neu_sa** module comprises several submodules and utilities to handle diverse tasks:

1. **Routers**: Define API endpoints and handle request routing.
2. **Agents**: Specialized agents that execute task-specific logic.
3. **Utils**: Shared utilities for backend processes such as eligibility recalculations.

Each component is designed to be modular and extensible for future enhancements.


## FastAPI Application Structure

### File: [`fastapp.py`](/backend/neu_sa/routers/fastapp.py)

Initializes the FastAPI application and includes the following routers:

- **Authentication Router** (`auth.py`): Handles user login, registration, and token validation.
- **User Router** (`user_router.py`): Manages user profiles and course updates.
- **Transcript Router** (`transcript_router.py`): Processes uploaded transcripts and manages S3 integrations.
- **Task Router** (`task_router.py`): Routes user queries to appropriate agents.

Code Snippet:

```python
from fastapi import FastAPI
from neu_sa.routers.auth import auth_router
from neu_sa.routers.user_router import user_router
from neu_sa.routers.transcript_router import transcript_router
from neu_sa.routers.task_router import task_router

app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(transcript_router, prefix="/transcripts", tags=["Transcript Processing"])
app.include_router(task_router, prefix="/chat", tags=["Task Detection and Query"])
```

---

## Submodules

### 1. **Routers**

#### [`auth.py`](/backend/neu_sa/routers/auth.py)
Handles user authentication:
- **Endpoints**: `/register`, `/login`, `/validate-token`
- **Password Validation**: Ensures strong passwords.
- **JWT Tokens**: Used for secure communication.

#### [`user_router.py`](/backend/neu_sa/routers/user_router.py)
Manages user data:
- **Endpoints**:
  - `/{user_id}`: Fetch user data.
  - `/{user_id}/profile`: Update user profile.
  - `/{user_id}/courses`: Update user courses with background eligibility recalculations.

#### [`transcript_router.py`](/backend/neu_sa/routers/transcript_router.py)
Processes transcripts:
- **Integration with AWS S3**: Upload and retrieve user transcripts.
- **AWS Textract**: Extracts structured data from uploaded transcripts.

#### [`task_router.py`](/backend/neu_sa/routers/task_router.py)
Handles query routing:
- Uses the compiled **StateGraph** to determine which agents to invoke and return the final response

### 2. **Agents**

#### [`agent.py`](/backend/neu_sa/agents/agent.py)
Defines the **StateGraph** to coordinate multi-agent workflows. Includes:
- **Task Detection Node**: Determines which nodes to invoke based on user queries.
- **General Information Node**: Searches for general university-related information.
- **Course Description Node**: Retrieves detailed descriptions of courses.
- **SQL Agent Node**: Retrieves structured data from Snowflake.
- **User Course Agent Node**: Fetches user-specific course details and eligibility.
- **Response Construction Node**: Constructs final responses based on all gathered data.

#### [`task_detection.py`](/backend/neu_sa/agents/task_detection.py)
Analyzes user queries and determines which agents to invoke using an OpenAI model.
- Outputs:
  - `nodes_to_visit`
  - `course_description_keywords`
  - `general_description`

#### [`sql_agent.py`](/backend/neu_sa/agents/sql_agent.py)
Generates and executes SQL queries:
- Uses schema descriptions to ensure accurate query generation.
- Handles retries and error correction.

#### [`user_course_agent.py`](/backend/neu_sa/agents/user_course_agent.py)
Fetches user-specific data:
- Retrieves user program details, eligibility, and completed courses from Snowflake.

#### [`general_information_agent.py`](/backend/neu_sa/agents/general_information_agent.py)
Searches for general information based on `general_description`:
- **Pinecone**: Retrieves indexed knowledge.
- **Tavily**: Performs web searches on Northeastern University’s domain.

#### [`course_description_agent.py`](/backend/neu_sa/agents/course_description_agent.py)
Retrieves course code, prerequsites, course descriptions:
- Searches Pinecone for detailed course information based on semantic matching of `course_description_keywords`.

#### [`response_construction.py`](/backend/neu_sa/agents/response_construction.py)
Constructs user responses:
- Integrates data from other agents to provide actionable and concise responses.

### 3. **Utils**

#### [`recalculate_eligibility.py`](/backend/neu_sa/agents/recalculate_eligibility.py)
Handles program-specific eligibility checks:
- Validates core, elective, and subject area requirements.
- Updates the `USER_ELIGIBILITY` table with recalculated data.

## How to Extend

1. **Adding a New Router**:
   - Create a new file under `routers`.
   - Define API endpoints using FastAPI’s `APIRouter`.
   - Include the router in `fastapp.py`.

2. **Adding a New Agent**:
   - Define the agent logic in `agents`.
   - Add the agent to the **StateGraph** in `agent.py`.
   - Create nodes and transitions for the new agent.

3. **Adding Utilities**:
   - Define reusable functions in `utils`.
   - Import them wherever required.

## Environment Variables
Ensure the following variables are set in the `.env` file:

```env
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
