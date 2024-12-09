from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from snowflake_setup import snowflake_setup
from load_program_requirements_data import load_program_requirements
from load_classes_data import insert_merged_data_to_snowflake
from scrape_course_catalog import scrape_and_save_to_s3
from load_course_catalog_to_snowflake import load_course_catalog_to_snowflake
from store_course_catalog_to_pinecone import store_course_catalog_to_pinecone
from scrape_resources import scrape_resources, chunk_and_index_resources
from scrape_graduation_Commencement import scrape_graduation_info, chunk_and_index_graduation
from Scrape_FAQ import scrape_faq, chunk_and_index_faq
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

def scrape_courses(**kwargs):
    subject_codes = ["info", "damg", "tele", "csye", "encp"]
    bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_key = "neu_data/all_courses.csv"
    df = scrape_and_save_to_s3(subject_codes, bucket_name, s3_key)
    kwargs['ti'].xcom_push(key='course_catalog_df', value=df.to_json())

def load_courses_to_snowflake(**kwargs):
    import pandas as pd
    ti = kwargs['ti']
    df_json = ti.xcom_pull(key='course_catalog_df')
    df = pd.read_json(df_json)
    load_course_catalog_to_snowflake(df)

def store_courses_in_pinecone(**kwargs):
    index_name = "course-catalog-index"
    import pandas as pd
    ti = kwargs['ti']
    df_json = ti.xcom_pull(key='course_catalog_df')
    df = pd.read_json(df_json)
    store_course_catalog_to_pinecone(df,index_name)

def process_resources(**kwargs):
    resources_text = scrape_resources()
    if resources_text:
        chunk_and_index_resources(resources_text)

def process_graduation_info(**kwargs):
    sections = scrape_graduation_info()
    if sections:
        chunk_and_index_graduation(sections)

def process_faq(**kwargs):
    faq_text = scrape_faq()
    if faq_text:
        chunk_and_index_faq(faq_text)
        
with DAG(
    'neu_data_ingestion_and_processing_pipeline',
    default_args=default_args,
    description='DAG to setup Snowflake, load course catalog, process university resources, and index in Pinecone',
    schedule_interval=None,
    start_date=datetime(2024, 12, 5),
    catchup=False,
) as dag:

    setup_snowflake_task = PythonOperator(
        task_id='setup_snowflake',
        python_callable=snowflake_setup
    )

    load_program_requirements_task = PythonOperator(
        task_id='load_program_requirements',
        python_callable=load_program_requirements
    )

    load_classes_data_task = PythonOperator(
        task_id='load_classes_data',
        python_callable=insert_merged_data_to_snowflake
    )

    scrape_course_catalog_task = PythonOperator(
        task_id='scrape_course_catalog',
        python_callable=scrape_courses,
        provide_context=True
    )

    load_course_catalog_to_snowflake_task = PythonOperator(
        task_id='load_course_catalog_to_snowflake',
        python_callable=load_courses_to_snowflake,
        provide_context=True
    )

    store_course_catalog_to_pinecone_task = PythonOperator(
        task_id='store_course_catalog_to_pinecone',
        python_callable=store_courses_in_pinecone,
        provide_context=True
    )

    process_resources_task = PythonOperator(
        task_id='process_resources',
        python_callable=process_resources,
        provide_context=True
    )

    process_graduation_info_task = PythonOperator(
        task_id='process_graduation_info',
        python_callable=process_graduation_info,
        provide_context=True
    )

    process_faq_task = PythonOperator(
        task_id='process_faq',
        python_callable=process_faq,
        provide_context=True
    )

    # Define task dependencies
    setup_snowflake_task >> load_program_requirements_task >> load_classes_data_task
    load_classes_data_task >> scrape_course_catalog_task >> load_course_catalog_to_snowflake_task >> store_course_catalog_to_pinecone_task
    process_resources_task >> process_graduation_info_task >> process_faq_task
