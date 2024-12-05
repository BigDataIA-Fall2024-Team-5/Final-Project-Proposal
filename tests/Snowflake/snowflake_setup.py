import snowflake.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def snowflake_setup():
    # Establish a connection to Snowflake using environment variables
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )

    # Create a cursor
    cursor = conn.cursor()

    # Get the database, schema, and table names from environment variables, or use default values
    database_name = os.getenv("SNOWFLAKE_DATABASE", "DB_NEU_SA")
    schema_name = os.getenv("SNOWFLAKE_SCHEMA", "NEU_SA")
    warehouse_name = os.getenv("SNOWFLAKE_WAREHOUSE", "WH_NEU_SA")

    try:
        # Script to create warehouse (if not exists)
        create_warehouse_script = f"""
        CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}
        WITH WAREHOUSE_SIZE = 'XSMALL'
        AUTO_SUSPEND = 300
        AUTO_RESUME = TRUE
        INITIALLY_SUSPENDED = TRUE;
        """

        # Script to create database
        create_database_script = f"CREATE DATABASE IF NOT EXISTS {database_name};"

        # Script to create schema (if not exists)
        create_schema_script = f"CREATE SCHEMA IF NOT EXISTS {database_name}.{schema_name};"

        # Scripts to create tables

        create_program_requirements_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.PROGRAM_REQUIREMENTS (
            PROGRAM_ID VARCHAR(25) PRIMARY KEY,
            PROGRAM_NAME VARCHAR(100),
            MAX_CREDIT_HOURS INT,
            MIN_GPA FLOAT,
            CORE_CREDIT_REQ INT,
            CORE_OPTIONS_CREDIT_REQ INT,
            ELECTIVE_CREDIT_REQ INT,
            SUBJECT_CREDIT_REQ INT,
            ELECTIVE_EXCEPTION VARCHAR(500)
        );
        """

        create_subject_areas_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.SUBJECT_AREAS (
            PROGRAM_ID VARCHAR(25) PRIMARY KEY,
            SUBJECT_CODE VARCHAR(10),
            MIN_CREDIT_HOURS INT
        );
        """

        create_core_requirements_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.CORE_REQUIREMENTS (
            PROGRAM_ID VARCHAR(25),
            COURSE_CODE VARCHAR(10),
            PRIMARY KEY (PROGRAM_ID, COURSE_CODE)
        );
        """
        create_core_options_requirements_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.CORE_OPTIONS_REQUIREMENTS (
            PROGRAM_ID VARCHAR(25),
            COURSE_CODE VARCHAR(10),
            PRIMARY KEY (PROGRAM_ID, COURSE_CODE)
        );
        """

        create_elective_requirements_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.ELECTIVE_REQUIREMENTS (
            PROGRAM_ID VARCHAR(25),
            SUBJECT_CODE VARCHAR(10),
            PRIMARY KEY (PROGRAM_ID, SUBJECT_CODE)
        );
        """

        create_user_profile_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.USER_PROFILE (
            USER_ID INT AUTOINCREMENT(1, 1) PRIMARY KEY,
            USERNAME VARCHAR(50),
            PASSWORD VARCHAR(200),
            GPA FLOAT,
            COMPLETED_CREDITS INT DEFAULT 0,
            CAMPUS VARCHAR(25),
            COLLEGE VARCHAR(50),
            PROGRAM_NAME VARCHAR(100),
            PROGRAM_ID VARCHAR(25),
            TRANSCRIPT_LINK VARCHAR(100)
        );
        """

        create_user_courses_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.USER_COURSES (
            USER_ID INT,
            COURSE_CODE VARCHAR(10),
            COURSE_NAME VARCHAR(50),
            GRADE VARCHAR(25),
            CREDITS FLOAT,
            PRIMARY KEY (USER_ID, COURSE_CODE),
            FOREIGN KEY (USER_ID) REFERENCES {database_name}.{schema_name}.USER_PROFILE(USER_ID)
        );
        """
        create_user_eligibility_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.USER_ELIGIBILITY (
            USER_ID INT NOT NULL,
            COURSE_OR_REQUIREMENT VARCHAR(25) NOT NULL,
            ELIGIBLE BOOLEAN, 
            DETAILS VARCHAR(500),
            STATUS VARCHAR(20) DEFAULT 'PENDING',
            CHECK_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (USER_ID, COURSE_OR_REQUIREMENT),
            FOREIGN KEY (USER_ID) REFERENCES {database_name}.{schema_name}.USER_PROFILE(USER_ID)
        );
        """

        create_classes_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.CLASSES (
            TERM VARCHAR(25),
            COURSE_CODE VARCHAR(10),
            CRN INT,
            CAMPUS VARCHAR(25),
            SCHEDULE_TYPE VARCHAR(50),
            INSTRUCTIONAL_METHOD VARCHAR(50),
            INSTRUCTOR VARCHAR(100),
            START_DATE DATE,
            END_DATE DATE,
            TIMING_LOCATION TEXT,
            ENROLLMENT_MAX INT,
            SEATS_AVAILABLE INT,
            WAITLIST_CAPACITY INT,
            WAITLIST_SEATS_AVAILABLE INT,
            PRIMARY KEY (TERM, COURSE_CODE, CRN)
        );
        """

        create_course_catalog_table = f"""
        CREATE OR REPLACE TABLE {database_name}.{schema_name}.COURSE_CATALOG (
            COURSE_CODE VARCHAR(10),
            COURSE_NAME VARCHAR(100),
            DESCRIPTION TEXT,
            PREREQUISITES TEXT,
            COREQUISITES TEXT,
            CREDITS FLOAT,
            SUBJECT_CODE VARCHAR(10),
            PRIMARY KEY (COURSE_CODE)
        );
        """

        # Execute scripts sequentially
        print(f"Creating warehouse '{warehouse_name}'...")
        cursor.execute(create_warehouse_script)
        print(f"Warehouse '{warehouse_name}' created or exists.")

        print(f"Creating database '{database_name}'...")
        cursor.execute(create_database_script)
        print(f"Database '{database_name}' created or exists.")

        print(f"Creating schema '{schema_name}'...")
        cursor.execute(create_schema_script)
        print(f"Schema '{schema_name}' created or exists.")

        print("Creating tables...")
        #cursor.execute(create_program_requirements_table)
        print("PROGRAM_REQUIREMENTS table created.")

        #cursor.execute(create_subject_areas_table)
        print("SUBJECT_AREAS table created.")

        #cursor.execute(create_core_requirements_table)
        print("CORE_REQUIREMENTS table created.")

        #cursor.execute(create_core_options_requirements_table)
        print("CORE_OPTIONS_REQUIREMENTS table created.")

        #cursor.execute(create_elective_requirements_table)
        print("ELECTIVE_REQUIREMENTS table created.")

        #cursor.execute(create_user_profile_table)
        print("USER_PROFILE table created.")

        #cursor.execute(create_user_courses_table)
        print("USER_COURSES table created.")

        #cursor.execute(create_user_eligibility_table)
        print("USER_ELIGIBILITY table created.")

        cursor.execute(create_classes_table)
        print("CLASSES table created.")

        #cursor.execute(create_course_catalog_table)
        print("COURSE_CATALOG table created.")

    except snowflake.connector.errors.ProgrammingError as e:
        print(f"Error during setup: {e}")

    finally:
        cursor.close()
        conn.close()
        print("Snowflake connection closed.")

if __name__ == "__main__":
    print("Starting Snowflake setup...")
    snowflake_setup()
    print("Snowflake setup complete.")
