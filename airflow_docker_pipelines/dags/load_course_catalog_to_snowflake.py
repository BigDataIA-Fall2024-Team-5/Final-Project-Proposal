import snowflake.connector
import os
from io import StringIO

def load_course_catalog_to_snowflake(df):
    """
    Load course catalog data from a DataFrame into the Snowflake `COURSE_CATALOG` table.
    """
    print("Loading course catalog data into Snowflake...")
    
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

        # Define the target table
        table_name = "COURSE_CATALOG"

        # Convert the DataFrame to CSV format in memory
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, header=False)  # Exclude headers for Snowflake COPY
        csv_buffer.seek(0)

        # Upload DataFrame to Snowflake using Snowflake's `MERGE`
        print(f"Creating temporary table TEMP_{table_name}...")
        cursor.execute(f"CREATE TEMPORARY TABLE IF NOT EXISTS TEMP_{table_name} LIKE {table_name};")
        print(f"Temporary table TEMP_{table_name} created.")

        print("Uploading data to Snowflake temporary table...")
        for _, row in df.iterrows():
            cursor.execute(
                f"""
                INSERT INTO TEMP_{table_name}
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["COURSE_CODE"],
                    row["COURSE_NAME"],
                    row["DESCRIPTION"],
                    row["PREREQUISITES"],
                    row["COREQUISITES"],
                    row["CREDITS"],
                    row["SUBJECT_CODE"],
                ),
            )

        print("Data uploaded to temporary table.")

        # Merge data into the target table
        print(f"Merging data into {table_name}...")
        cursor.execute(f"""
            MERGE INTO {table_name} AS target
            USING TEMP_{table_name} AS source
            ON target.COURSE_CODE = source.COURSE_CODE
            WHEN MATCHED THEN UPDATE SET
                COURSE_NAME = source.COURSE_NAME,
                DESCRIPTION = source.DESCRIPTION,
                PREREQUISITES = source.PREREQUISITES,
                COREQUISITES = source.COREQUISITES,
                CREDITS = source.CREDITS,
                SUBJECT_CODE = source.SUBJECT_CODE
            WHEN NOT MATCHED THEN INSERT (
                COURSE_CODE, COURSE_NAME, DESCRIPTION, PREREQUISITES, COREQUISITES, CREDITS, SUBJECT_CODE
            ) VALUES (
                source.COURSE_CODE, source.COURSE_NAME, source.DESCRIPTION, source.PREREQUISITES, source.COREQUISITES, source.CREDITS, source.SUBJECT_CODE
            );
        """)
        print(f"Data merged successfully into {table_name}.")

        # Commit and close the connection
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error loading course catalog data into Snowflake: {e}")
