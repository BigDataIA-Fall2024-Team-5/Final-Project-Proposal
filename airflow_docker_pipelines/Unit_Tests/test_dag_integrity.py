# Import required Airflow module
from airflow.models import DagBag

def test_dag_integrity():
    """
    Function to test the integrity of all DAGs in the specified folder.

    This function loads DAGs from the 'airflow_docker_pipelines/dags' folder 
    and checks for any import errors. If errors are found, the test fails 
    and displays the corresponding error messages.
    """
    
    # Initialize the DagBag by specifying the DAG folder path
    dag_bag = DagBag(
        dag_folder='airflow_docker_pipelines/dags', 
        include_examples=False
    )

    # Check if there are any import errors
    if dag_bag.import_errors:
        # Format the error messages for better readability
        error_messages = "\n".join(
            f"DAG: {dag_id}, Error: {str(error)}"
            for dag_id, error in dag_bag.import_errors.items()
        )

        # Raise an assertion error with detailed messages
        assert False, f"DAG import errors detected:\n{error_messages}"
    else:
        print("All DAGs loaded successfully without errors.")