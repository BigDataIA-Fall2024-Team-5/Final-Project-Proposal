import os
import boto3
import snowflake.connector

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# Snowflake Configuration
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
    )

def check_s3_file_exists(bucket_name, s3_key):
    """Check if a file exists in the specified S3 bucket."""
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except boto3.exceptions.botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise

def insert_data_to_snowflake_from_s3(s3_key):
    """Insert data from S3 into Snowflake, avoiding duplicates."""
    try:
        # Check if the S3 file exists
        if not check_s3_file_exists(S3_BUCKET_NAME, s3_key):
            print(f"File '{s3_key}' does not exist in S3 bucket '{S3_BUCKET_NAME}'.")
            print("Run web scrapping NU Banner pipeline first.")
            return
        
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        # Define table names
        stage_name = "CLASSES_STAGE"
        staging_table = "CLASSES_TEMP"
        target_table = "CLASSES"
        
        # Create temporary stage if not exists
        cursor.execute(f"CREATE TEMPORARY STAGE IF NOT EXISTS {stage_name}")
        print(f"Stage {stage_name} created/exists.")
        
        # Create a temporary staging table
        cursor.execute(f"""
            CREATE TEMPORARY TABLE IF NOT EXISTS {staging_table} LIKE {target_table};
        """)
        print(f"Temporary table {staging_table} created/exists.")
        
        # Load data into the staging table from S3
        cursor.execute(f"""
            COPY INTO {staging_table}
            FROM 's3://{S3_BUCKET_NAME}/{s3_key}'
            CREDENTIALS = (
                AWS_KEY_ID='{AWS_ACCESS_KEY_ID}'
                AWS_SECRET_KEY='{AWS_SECRET_ACCESS_KEY}'
            )
            FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' EMPTY_FIELD_AS_NULL = TRUE)
            ON_ERROR = 'CONTINUE'
        """)
        print(f"Data loaded into staging table {staging_table}.")
        
        # Insert new records into the target table, avoiding duplicates
        cursor.execute(f"""
            INSERT INTO {target_table}
            SELECT *
            FROM {staging_table}
            WHERE (TERM, COURSE_CODE, CRN) NOT IN (
                SELECT TERM, COURSE_CODE, CRN
                FROM {target_table}
            );
        """)
        print(f"New data inserted into {target_table}.")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting data to Snowflake: {e}")

def insert_merged_data_to_snowflake():
    """Insert merged data into Snowflake."""
    merged_s3_key = "neu_data/all_classes.csv"
    insert_data_to_snowflake_from_s3(merged_s3_key)
