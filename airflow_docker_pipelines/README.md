# Airflow Pipeline README

This README provides a comprehensive guide to set up, run, and manage the **Airflow Pipeline** for data ingestion, processing, and storage in a Dockerized environment.

The Airflow pipeline automates the following tasks:
- Scraping course data from NU Banner.
- Loading course catalogs and program requirements into Snowflake.
- Indexing data into Pinecone for efficient search.
- Processing additional resources like FAQs and graduation information.

This setup leverages Docker for consistent deployment and reproducibility.

## Setup Instructions

### 1. Prerequisites
Ensure you have the following installed:
- Docker and Docker Compose
- Python 3.11

### 2. Navigate to the Airflow Directory
```bash
cd airflow_docker_pipelines
```

### 3. Build Docker Image for Airflow
```bash
docker build -t sa-image .
```

### 4. Run Airflow Initialization and Start Services
Replace placeholder values with your credentials before running the commands below.

#### Initialize Airflow
```bash
AIRFLOW_IMAGE_NAME=sa-image:latest AIRFLOW_UID=0 _AIRFLOW_WWW_USER_USERNAME=admin _AIRFLOW_WWW_USER_PASSWORD=admin123 AWS_ACCESS_KEY_ID='<YOUR_AWS_ACCESS_KEY>' AWS_SECRET_ACCESS_KEY='<YOUR_AWS_SECRET_KEY>' AWS_REGION='<YOUR_AWS_REGION>' S3_BUCKET_NAME='<YOUR_S3_BUCKET>' SNOWFLAKE_ACCOUNT='<YOUR_SNOWFLAKE_ACCOUNT>' SNOWFLAKE_USER='<YOUR_SNOWFLAKE_USER>' SNOWFLAKE_PASSWORD='<YOUR_SNOWFLAKE_PASSWORD>' SNOWFLAKE_ROLE='<YOUR_SNOWFLAKE_ROLE>' NVIDIA_API_KEY='<YOUR_NVIDIA_API_KEY>' PINECONE_API_KEY='<YOUR_PINECONE_API_KEY>' docker-compose up airflow-init
```

#### Start Airflow Services
```bash
AIRFLOW_IMAGE_NAME=sa-image:latest AIRFLOW_UID=0 _AIRFLOW_WWW_USER_USERNAME=admin _AIRFLOW_WWW_USER_PASSWORD=admin123 AWS_ACCESS_KEY_ID='<YOUR_AWS_ACCESS_KEY>' AWS_SECRET_ACCESS_KEY='<YOUR_AWS_SECRET_KEY>' AWS_REGION='<YOUR_AWS_REGION>' S3_BUCKET_NAME='<YOUR_S3_BUCKET>' SNOWFLAKE_ACCOUNT='<YOUR_SNOWFLAKE_ACCOUNT>' SNOWFLAKE_USER='<YOUR_SNOWFLAKE_USER>' SNOWFLAKE_PASSWORD='<YOUR_SNOWFLAKE_PASSWORD>' SNOWFLAKE_ROLE='<YOUR_SNOWFLAKE_ROLE>' NVIDIA_API_KEY='<YOUR_NVIDIA_API_KEY>' PINECONE_API_KEY='<YOUR_PINECONE_API_KEY>' docker-compose up -d
```

## Pipeline Structure

### Main Components

- **Data Ingestion**: Scrapes and merges data from NU Banner.
- **Snowflake Integration**: Loads course catalogs and program requirements.
- **Pinecone Indexing**: Stores searchable data.
- **Resource Processing**: Scrapes FAQs, graduation information, and additional university resources.

### Input Data Format
For NU Banner scraping, ensure data follows this format:

```python
'calls': [
    ("Fall 2024 Semester", "202510", "Information Systems", "INFO"),
    ("Fall 2024 Semester", "202510", "Computer Systems Engineering", "CSYE"),
]
```
- **Semester Code**: Retrieved from NU Banner HTML for the selected semester.
- **Departments**: Expand `calls` with additional subject codes as needed.

## DAG Descriptions

### 1. `DAG_main_pipeline.py`
**Purpose**: Orchestrates data ingestion, processing, and indexing workflows.

**Tasks:**
- `setup_snowflake`: Configures Snowflake schemas and tables.
- `load_program_requirements`: Loads program requirement data.
- `load_classes_data`: Loads and processes merged class data.
- `scrape_course_catalog`: Scrapes course data and saves it to S3.
- `load_course_catalog_to_snowflake`: Loads the scraped catalog into Snowflake.
- `store_course_catalog_to_pinecone`: Indexes course catalog in Pinecone.
- `process_resources`: Scrapes and indexes university resources.
- `process_graduation_info`: Scrapes and indexes graduation information.
- `process_faq`: Scrapes and indexes FAQ data.

**Task Flow:**
```text
setup_snowflake -> load_program_requirements -> load_classes_data -> scrape_course_catalog -> load_course_catalog_to_snowflake -> store_course_catalog_to_pinecone -> [process_resources, process_graduation_info, process_faq]
```

### 2. `DAG_scrapenubanner_pipeline.py`
**Purpose**: Scrapes NU Banner data for specific semesters and merges results.

**Tasks:**
- `collect_fall_2023`: Scrapes Fall 2023 semester data.
- `collect_spring_2024`: Scrapes Spring 2024 semester data.
- `collect_fall_2024`: Scrapes Fall 2024 semester data.
- `collect_spring_2025`: Scrapes Spring 2025 semester data.
- `merge_semester_data`: Merges all semester files into a single dataset.

**Task Flow:**
```text
[collect_fall_2023, collect_spring_2024, collect_fall_2024, collect_spring_2025] -> merge_semester_data
```
