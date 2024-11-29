import pandas as pd
import boto3
import os
import snowflake.connector
from io import StringIO

# Fetch CSV from S3 and load into DataFrame
def fetch_csv_from_s3(bucket_name, s3_key):
    print("Fetching CSV from S3...")
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
    csv_data = response['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_data))
    print(f"CSV fetched successfully from S3: s3://{bucket_name}/{s3_key}")
    return df
import pandas as pd
import snowflake.connector
import os
from io import StringIO

def clean_dataframe(df):
    """Clean DataFrame to handle NaN and ensure proper data types."""
    print("Cleaning DataFrame...")
    # Replace NaN values with None
    df = df.where(pd.notnull(df), None)

    # Convert dates to Snowflake-compatible format
    if 'START_DATE' in df.columns:
        df['START_DATE'] = pd.to_datetime(df['START_DATE']).dt.strftime('%Y-%m-%d')
    if 'END_DATE' in df.columns:
        df['END_DATE'] = pd.to_datetime(df['END_DATE']).dt.strftime('%Y-%m-%d')

    # Ensure proper data types for numerical columns
    for column in ['CRN', 'ENROLLMENT_MAX', 'SEATS_AVAILABLE', 'WAITLIST_CAPACITY', 'WAITLIST_SEATS_AVAILABLE']:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0).astype(int)

    print("DataFrame cleaned successfully.")
    return df

def insert_data_to_snowflake(df, table_name):
    """Insert or update data in Snowflake using temporary table and MERGE."""
    print("Connecting to Snowflake...")
    try:
        # Establish Snowflake connection
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
            database=os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA"),
        )
        cursor = conn.cursor()

        # Convert DataFrame column names to match Snowflake schema
        print("Renaming DataFrame columns to match Snowflake schema...")
        df.columns = [
            "TERM", "COURSE_CODE", "CRN", "CAMPUS", "SCHEDULE_TYPE",
            "INSTRUCTIONAL_METHOD", "INSTRUCTOR", "START_DATE", "END_DATE",
            "TIMING_LOCATION", "ENROLLMENT_MAX", "SEATS_AVAILABLE",
            "WAITLIST_CAPACITY", "WAITLIST_SEATS_AVAILABLE"
        ]
        print("DataFrame Columns After Renaming:", df.columns.tolist())

        # Create temporary table
        temp_table_name = f"TEMP_{table_name}"
        print(f"Creating temporary table {temp_table_name}...")
        cursor.execute(f"CREATE TEMPORARY TABLE {temp_table_name} LIKE {table_name};")
        print(f"Temporary table {temp_table_name} created.")

        # Upload data row by row to the temporary table
        print(f"Uploading data to {temp_table_name}...")
        for index, row in df.iterrows():
            cursor.execute(
                f"""
                INSERT INTO {temp_table_name}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["TERM"],
                    row["COURSE_CODE"],
                    row["CRN"],
                    row["CAMPUS"],
                    row["SCHEDULE_TYPE"],
                    row["INSTRUCTIONAL_METHOD"],
                    row["INSTRUCTOR"],
                    row["START_DATE"],
                    row["END_DATE"],
                    row["TIMING_LOCATION"],
                    row["ENROLLMENT_MAX"],
                    row["SEATS_AVAILABLE"],
                    row["WAITLIST_CAPACITY"],
                    row["WAITLIST_SEATS_AVAILABLE"],
                ),
            )
        print(f"Data uploaded to {temp_table_name}.")

        # Merge data from the temporary table into the target table
        print(f"Merging data into {table_name}...")
        merge_query = f"""
            MERGE INTO {table_name} AS target
            USING {temp_table_name} AS source
            ON target.TERM = source.TERM AND target.COURSE_CODE = source.COURSE_CODE AND target.CRN = source.CRN
            WHEN MATCHED THEN UPDATE SET
                CAMPUS = source.CAMPUS,
                SCHEDULE_TYPE = source.SCHEDULE_TYPE,
                INSTRUCTIONAL_METHOD = source.INSTRUCTIONAL_METHOD,
                INSTRUCTOR = source.INSTRUCTOR,
                START_DATE = source.START_DATE,
                END_DATE = source.END_DATE,
                TIMING_LOCATION = source.TIMING_LOCATION,
                ENROLLMENT_MAX = source.ENROLLMENT_MAX,
                SEATS_AVAILABLE = source.SEATS_AVAILABLE,
                WAITLIST_CAPACITY = source.WAITLIST_CAPACITY,
                WAITLIST_SEATS_AVAILABLE = source.WAITLIST_SEATS_AVAILABLE
            WHEN NOT MATCHED THEN INSERT (
                TERM, COURSE_CODE, CRN, CAMPUS, SCHEDULE_TYPE, INSTRUCTIONAL_METHOD,
                INSTRUCTOR, START_DATE, END_DATE, TIMING_LOCATION, ENROLLMENT_MAX,
                SEATS_AVAILABLE, WAITLIST_CAPACITY, WAITLIST_SEATS_AVAILABLE
            ) VALUES (
                source.TERM, source.COURSE_CODE, source.CRN, source.CAMPUS, source.SCHEDULE_TYPE,
                source.INSTRUCTIONAL_METHOD, source.INSTRUCTOR, source.START_DATE, source.END_DATE,
                source.TIMING_LOCATION, source.ENROLLMENT_MAX, source.SEATS_AVAILABLE,
                source.WAITLIST_CAPACITY, source.WAITLIST_SEATS_AVAILABLE
            );
        """
        cursor.execute(merge_query)
        print(f"Data merged successfully into {table_name}.")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting data into Snowflake: {e}")


def main():
    # Replace this with the actual DataFrame loading logic
    # Example: fetch_csv_from_s3(bucket_name, s3_key)
    table_name = "CLASSES"
    bucket_name = "neu-sa"
    s3_key = "neu_data/all_classes.csv"

    print("Fetching and cleaning data...")
    # Assuming fetch_csv_from_s3 is already defined
    df = fetch_csv_from_s3(bucket_name, s3_key)
    df = clean_dataframe(df)

    print("Inserting data into Snowflake...")
    insert_data_to_snowflake(df, table_name)

# Run the script
if __name__ == "__main__":
    main()
