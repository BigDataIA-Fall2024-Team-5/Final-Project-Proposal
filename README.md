
# Northeastern-University-Student-Assistance-Chatbot

## Links
- **Project Proposal**: [[CodeLabs](https://codelabs-preview.appspot.com/?file_id=1bf-PQCwhOEHs6vVuYpJwY-ejyBHMTnJIuw2xpblkg0A#0)] 
- **Final CodeLab**: [[CodeLabs]( )] [[Google Drive Link]( )] [[Github Location]( )]
- **Presentation**: [[Google Drive]( )]
- **Deployed FastAPI**: [[FastAPI Service]( )]
- **Deployed Streamlit**: [[Streamlit App]( )]
- **Docker Repository**: [[DockerHub](https://hub.docker.com/repositories/dharunramaraj)]
- **GitHub Project**: [[GitHub](https://github.com/orgs/BigDataIA-Fall2024-Team-5/projects/13)]

## Architecture Diagram
![image]( )


## Table of Contents
1. [Introduction](#introduction)
2. [Key Features](#key-features)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Usage](#usage)
6. [License](#license)

## Introduction

**NEU-SAC** is an intelligent and user-friendly platform designed to simplify course planning and general queries for graduate students at Northeastern University. By leveraging cutting-edge technologies like multi-agent architecture, RAG, data pipelines, and natural language processing, This **Student-Assistance-Chatbot** provides:

**Personalized Course Recommendations**: Tailored to the student’s program, completed courses, and academic standing.
**General Query Assistance**: A chatbot that answers questions related to university policies, course schedules, and registration processes.
**Streamlined Course Information**: Aggregating details such as CRNs, professors, timings, and campus locations in one place.

This project enhances the student experience by reducing the time spent navigating multiple platforms, ensuring better course planning and decision-making, and offering scalable solutions for academic institutions.

## Key Features

- **Multi-Agent Chatbot**: A sophisticated chatbot system powered by specialized agents to handle semantic, structured, and hybrid queries.

  - **Task Detection Agent**: Serves as the primary orchestrator, analyzing user queries to determine their intent and routing them to appropriate agents.
  - **General Information Agent**: Handles FAQs and performs semantic searches. If a proper match is not found (based on a score threshold), it falls back to web search within the northeastern.edu domain to provide relevant information.
  - **Course Description Agent**: Utilizes the indexed course catalog in Pinecone, which contains course names and descriptions in chunks, to suggest courses for users. The metadata includes course code, course name, and course description. It retrieves this information and passes it to the next agent for further processing or response construction.
  - **SQL Agent**: Retrieves structured data from Snowflake, including course schedules, program details, instructors, and room locations.
  - **User Course Agent**: Fetches user-specific details from Snowflake, such as completed courses, GPA, and credits. It provides necessary data for eligibility decisions and personalized recommendations.
  - **Response Construction Agent**: Aggregates data from various agents, including the User Course Agent, and constructs a comprehensive, user-friendly response. It makes final decisions based on all gathered information, ensuring clarity and relevance.

- **Personalized Course Recommendations**: Utilizes user transcripts, program requirements, and real-time eligibility checks to suggest suitable courses with details like CRNs, professors, and class timings.

- **Automated Data Pipelines**: Built with Apache Airflow, these pipelines scrape and ingest data from course registration pages, program requirements, and course catalogs, general information page ensuring that information remains current and accurate.

- **Transcript Processing**: Employs Amazon Textract to extract data from user-uploaded transcripts, automatically updating eligibility and completed courses.

- **Centralized Information Access**: Combines course registration data, catalog descriptions, program requirements, and seat availability into a unified platform for easy access.

- **Scalability and Extensibility**: Modular architecture and API-driven design enable the platform to be easily extended to support other universities or programs.

## Project Structure

📂 **Northeastern-University-Student-Assistance-Chatbot**  
├── **[LICENSE](LICENSE)**  
├── **[README.md](README.md)**  
├── **docker-compose.yml**  
├── 📂 **[airflow_docker_pipelines](airflow_docker_pipelines/README.md)**  
│   ├── **Dockerfile**  
│   ├── **docker-compose.yaml**  
│   ├── 📂 **dags**  
│   │   ├── `DAG_main_pipeline.py`  
│   │   ├── `DAG_scrapenubanner_pipeline.py`  
│   │   ├── Other supporting scripts for the DAGs (e.g. `load_classes_data.py`, `scrape_course_catalog.py`, `store_course_catalog_to_pinecone.py`)  
├── 📂 **[backend](backend/README.md)**  
│   ├── **Dockerfile**  
│   ├── `poetry.lock`  
│   ├── `pyproject.toml`  
│   ├── 📂 **neu_sa**  
│   │   ├── 📂 **agents**  
│   │   │   ├── Agents for processing tasks (e.g. `sql_agent.py`, `general_information_agent.py`, `task_detection.py`)  
│   │   ├── 📂 **routers**  
│   │   │   ├── `auth.py`  
│   │   │   ├── `task_router.py`  
│   │   │   ├── `transcript_router.py`  
│   │   │   └── `user_router.py`  
│   │   ├── 📂 **utils**  
│   │   │   ├── `recalculate_eligibility.py`  
├── 📂 **[frontend](frontend/README.md)**  
│   ├── **Dockerfile**  
│   ├── `poetry.lock`  
│   ├── `pyproject.toml`  
│   ├── `app.py`  
│   ├── 📂 **streamlit_pages**  
│   │   ├── `login_page.py`  
│   │   ├── `register_page.py`  
│   │   ├── `update_details_page.py`  
│   │   ├── `user_main_page.py`  

## Installation

### Prerequisites
- **Docker & Docker Compose**: Required for containerization.
- **Python 3.11**: Ensure compatibility with Python 3.11.
- **API Credentials**: Set up AWS, Snowflake, NVIDIA, Pinecone, Tavily and OpenAI credentials in the `.env` file.
- **Poetry**: Required for dependency management.

### Setup Steps
1. **Clone the Repository**:
```bash
git clone https://github.com/BigDataIA-Fall2024-Team-5/Northeastern-University-Student-Assistance-Chatbot.git
cd Northeastern-University-Student-Assistance-Chatbot
```
2. **Airflow Pipeline Setup**:
**Navigate to the Airflow Directory**:

```bash
cd airflow_docker_pipelines
```

**Build Docker Image for Airflow**:
```bash
docker build -t sa-image .
```
**Run Airflow Initialization with Environment Variables and then compose up**:
Replace the placeholder values with your credentials before running.
```bash
AIRFLOW_IMAGE_NAME=sa-image:latest AIRFLOW_UID=0 _AIRFLOW_WWW_USER_USERNAME=admin _AIRFLOW_WWW_USER_PASSWORD=admin123 AWS_ACCESS_KEY_ID='<YOUR_AWS_ACCESS_KEY>' AWS_SECRET_ACCESS_KEY='<YOUR_AWS_SECRET_KEY>' AWS_REGION='<YOUR_AWS_REGION>' S3_BUCKET_NAME='<YOUR_S3_BUCKET>' SNOWFLAKE_ACCOUNT='<YOUR_SNOWFLAKE_ACCOUNT>' SNOWFLAKE_USER='<YOUR_SNOWFLAKE_USER>' SNOWFLAKE_PASSWORD='<YOUR_SNOWFLAKE_PASSWORD>' SNOWFLAKE_ROLE='<YOUR_SNOWFLAKE_ROLE>' NVIDIA_API_KEY='<YOUR_NVIDIA_API_KEY>' PINECONE_API_KEY='<YOUR_PINECONE_API_KEY>' docker-compose up airflow-init
``` 
```bash
AIRFLOW_IMAGE_NAME=sa-image:latest AIRFLOW_UID=0 _AIRFLOW_WWW_USER_USERNAME=admin _AIRFLOW_WWW_USER_PASSWORD=admin123 AWS_ACCESS_KEY_ID='<YOUR_AWS_ACCESS_KEY>' AWS_SECRET_ACCESS_KEY='<YOUR_AWS_SECRET_KEY>' AWS_REGION='<YOUR_AWS_REGION>' S3_BUCKET_NAME='<YOUR_S3_BUCKET>' SNOWFLAKE_ACCOUNT='<YOUR_SNOWFLAKE_ACCOUNT>' SNOWFLAKE_USER='<YOUR_SNOWFLAKE_USER>' SNOWFLAKE_PASSWORD='<YOUR_SNOWFLAKE_PASSWORD>' SNOWFLAKE_ROLE='<YOUR_SNOWFLAKE_ROLE>' NVIDIA_API_KEY='<YOUR_NVIDIA_API_KEY>' PINECONE_API_KEY='<YOUR_PINECONE_API_KEY>' docker-compose up -d
```
- **Run Pipelines**:
    - **DAG_scrapenubanner_pipeline**: Automates scraping of semester-wise class details from the NU Banner system and saves the data as CSV files in Amazon S3 for further processing.
    - **DAG_main_pipeline**: A comprehensive pipeline that:
        - Initializes and sets up Snowflake for data storage.
        - Loads program requirements, class data, and course catalog into Snowflake.
        - Scrapes the course catalog and stores it in Amazon S3, Pinecone, and Snowflake.
        - Scrapes general information webpages and stores relevant data in a Pinecone index for efficient retrieval.

3. **Enviroment Variables Setup**
In the **parent directory** of frontend, backend:
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

BACKEND_URL='http://localhost:8000'
```

4. **Application Setup (Method 1 - Direct)**:
**Backend Setup**:
```bash
cd backend
poetry install
poetry run backend
```
**Frontend Setup**:
```bash
cd frontend
poetry install
poetry run streamlit run app.py
```
4. Application Setup (Method 2 - Docker Compose):
```bash
docker-compose up
```

## Usage

### 1. **Accessing the Application**
Once the application is running:
- **Frontend**: Accessible at `http://localhost:8501` (default Streamlit port).
- **Backend**: Available at `http://localhost:8000` for API calls and task orchestration.
- **Airflow Interface**: Accessible at `http://localhost:8080` for pipeline management.

### 2. **Chatbot Features**
- **General Information**:
  - Ask open-ended or specific questions like "How do I register for a course?" or "What are the GPA requirements for the MSIS program?".
  - The chatbot retrieves relevant answers using indexed data and, if necessary, performs web searches within the northeastern.edu domain.

- **Course Recommendations**:
  - Upload your transcript to receive personalized course suggestions based on completed courses, GPA, and program requirements.
  - View detailed course information, including CRNs, professors, schedules, and prerequisites.

### 3. **NU Banner Scraping**
To scrape semester-specific course details from NU Banner, the pipeline requires the following format:

```python
'semester_name': 'Fall_2024',
'calls': [
    ("Fall 2024 Semester", "202510", "Computer Systems Engineering", "CSYE"),
    # Add more courses here using the same format
    ("Fall 2024 Semester", "202510", "Information Systems", "INFO"),
]
```

- **Semester Code**: Found in the NU Banner HTML page for the selected semester (e.g., `202510` for Fall 2024).
- **Add More Courses**: Expand the list of `calls` with additional departments and subject codes for comprehensive scraping.

### 6. **Extending the Application**
- **Adding New Data Sources**:
  - Modify existing Airflow pipelines or create new DAGs to incorporate additional data sources.
- **Custom Queries**:
  - Update agents in the backend (`neu_sa/agents`) to handle new types of queries or enhance existing ones.
- **Scaling for Other Universities**:
  - Adjust scraping scripts and program-specific requirements to adapt the platform for other institutions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
