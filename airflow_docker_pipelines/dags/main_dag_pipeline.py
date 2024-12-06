from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from snowflake_setup import snowflake_setup
from load_program_requirements_data import load_program_requirements
from load_classes_data import insert_merged_data_to_snowflake
from scrape_course_catalog import scrape_and_save_to_s3
from load_course_catalog_to_snowflake import load_course_catalog_to_snowflake
from store_course_catalog_to_pinecone import store_course_catalog_to_pinecone

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

def scrape_courses(**kwargs):
    subject_codes = ["info", "damg", "tele", "csye", "encp"]
    bucket_name = "neu-sa-test"
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
    index_name = "course-catalog-index-test"
    import pandas as pd
    ti = kwargs['ti']
    df_json = ti.xcom_pull(key='course_catalog_df')
    df = pd.read_json(df_json)
    store_course_catalog_to_pinecone(df,index_name)

with DAG(
    'snowflake_setup_and_load_data_dag',
    default_args=default_args,
    description='DAG to setup Snowflake, load course catalog, and store in Pinecone',
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

    setup_snowflake_task >> load_program_requirements_task >> load_classes_data_task
    load_classes_data_task >> scrape_course_catalog_task >> load_course_catalog_to_snowflake_task >> store_course_catalog_to_pinecone_task

