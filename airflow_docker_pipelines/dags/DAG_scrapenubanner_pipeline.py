from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from nubanner_utils import (
    collect_data_by_semester,
    merge_all_semesters
)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

# Define the DAG
with DAG(
    'collect_and_merge_class_data',
    default_args=default_args,
    description='DAG to scrape, save, and merge class data',
    schedule_interval=None,
    start_date=datetime(2024, 12, 5),
    catchup=False,
) as dag:

    # Task 1: Collect data for Fall 2023
    collect_fall_2023_task = PythonOperator(
        task_id='collect_fall_2023',
        python_callable=collect_data_by_semester,
        op_kwargs={
            'semester_name': 'Fall_2023',
            'calls': [
                ("Fall 2023 Semester", "202410", "Computer Systems Engineering", "CSYE"),
            ]
        }
    )

    # Task 2: Collect data for Spring 2024
    collect_spring_2024_task = PythonOperator(
        task_id='collect_spring_2024',
        python_callable=collect_data_by_semester,
        op_kwargs={
            'semester_name': 'Spring_2024',
            'calls': [
                ("Spring 2024 Semester", "202430", "Computer Systems Engineering", "CSYE"),
            ]
        }
    )

    # Task 3: Collect data for Fall 2024
    collect_fall_2024_task = PythonOperator(
        task_id='collect_fall_2024',
        python_callable=collect_data_by_semester,
        op_kwargs={
            'semester_name': 'Fall_2024',
            'calls': [
                ("Fall 2024 Semester", "202510", "Computer Systems Engineering", "CSYE"),
            ]
        }
    )

    # Task 4: Collect data for Spring 2025
    collect_spring_2025_task = PythonOperator(
        task_id='collect_spring_2025',
        python_callable=collect_data_by_semester,
        op_kwargs={
            'semester_name': 'Spring_2025',
            'calls': [
                ("Spring 2025 Semester", "202530", "Computer Systems Engineering", "CSYE"),
            ]
        }
    )

    # Task 5: Merge all semester files into one
    merge_semester_data_task = PythonOperator(
        task_id='merge_semester_data',
        python_callable=merge_all_semesters,
        op_kwargs={
            'file_names': [
                "neu_data/Fall_2023_classes.csv",
                "neu_data/Spring_2024_classes.csv",
                "neu_data/Fall_2024_classes.csv",
                "neu_data/Spring_2025_classes.csv",
            ]
        }
    )

    # Define task dependencies
    [
        collect_fall_2023_task,
        collect_spring_2024_task,
        collect_fall_2024_task,
        collect_spring_2025_task
    ] >> merge_semester_data_task
