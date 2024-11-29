from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from selenium.common.exceptions import WebDriverException
import boto3
import os
import snowflake.connector
from io import StringIO

def init_driver():
    """Initialize Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)  # Ensure ChromeDriver is in PATH
    return driver

def fetch_class_details(driver, subject_code):
    """Extract class details."""
    try:
        popup_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section[aria-labelledby='classDetails']"))
        )

        section_text = popup_section.text
        course_number = popup_section.find_element(By.ID, "courseNumber").text.strip()
        details = {
            "term": section_text.split("Associated Term:")[1].split("\n")[0].strip(),
            "course_code": f"{subject_code} {course_number}",
            "crn": popup_section.find_element(By.ID, "courseReferenceNumber").text.strip(),
            "campus": section_text.split("Campus:")[1].split("\n")[0].strip(),
            "schedule_type": section_text.split("Schedule Type:")[1].split("\n")[0].strip(),
            "instructional_method": section_text.split("Instructional Method:")[1].split("\n")[0].strip(),
        }
        return details
    except Exception as e:
        print(f"Error fetching class details: {e}")
        return {}

def fetch_instructor_meeting_times(driver):
    """Extract instructor and meeting times."""
    try:
        instructor_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h3[@id='facultyMeetingTimes']/a"))
        )
        instructor_tab.click()

        meeting_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "meeting-faculty"))
        )
        instructors = "; ".join(
            [element.text for element in meeting_content.find_elements(By.CSS_SELECTOR, "span.meeting-faculty-member a")]
        )

        # Extract start and end dates
        dates = meeting_content.find_element(By.CLASS_NAME, "dates").text
        start_date, end_date = dates.split(" - ") if " - " in dates else (dates, "")

        # Extract combined timing and location details
        timing_location = meeting_content.find_element(By.CLASS_NAME, "right").text

        return {
            "instructor": instructors,
            "start_date": start_date.strip(),
            "end_date": end_date.strip(),
            "timing_location": timing_location.strip(),
        }
    except Exception as e:
        print(f"Error fetching instructor/meeting times: {e}")
        return {}

def fetch_enrollment_details(driver):
    """Extract enrollment and waitlist details."""
    try:
        enrollment_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h3[@id='enrollmentInfo']/a"))
        )
        enrollment_tab.click()

        enrollment_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section[aria-labelledby='enrollmentInfo']"))
        )

        details = {
            "enrollment_max": enrollment_section.find_element(By.XPATH, ".//span[contains(text(), 'Enrollment Maximum:')]/following-sibling::span").text.strip(),
            "seats_available": enrollment_section.find_element(By.XPATH, ".//span[contains(text(), 'Enrollment Seats Available:')]/following-sibling::span").text.strip(),
            "waitlist_capacity": enrollment_section.find_element(By.XPATH, ".//span[contains(text(), 'Waitlist Capacity:')]/following-sibling::span").text.strip(),
            "waitlist_seats_available": enrollment_section.find_element(By.XPATH, ".//span[contains(text(), 'Waitlist Seats Available:')]/following-sibling::span").text.strip(),
        }
        return details
    except Exception as e:
        print(f"Error fetching enrollment details: {e}")
        return {}

def main(term, term_id, program, subject_code):
    driver = init_driver()
    data = []  # List to store all course details

    try:
        driver.get("https://nubanner.neu.edu/StudentRegistrationSsb/ssb/registration/registration")
        print(f"Page loaded: {term}, {program}, {subject_code}.")

        browse_classes_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "classSearchLink"))
        )
        browse_classes_link.click()
        print("Navigated to Browse Classes.")

        term_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "select2-choice"))
        )
        term_dropdown.click()

        term_search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "s2id_autogen1_search"))
        )
        term_search_input.send_keys(term)
        time.sleep(2)

        matching_term = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[@id='{term_id}']"))
        )
        matching_term.click()

        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "term-go"))
        )
        continue_button.click()

        subject_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.select2-choices input.select2-input"))
        )
        subject_input.send_keys(program)
        time.sleep(2)

        matching_subject = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[@id='{subject_code}']"))
        )
        matching_subject.click()

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "search-go"))
        )
        search_button.click()
        print("Search completed.")

        total_pages_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.paging-text.total-pages"))
        )
        total_pages = int(total_pages_element.text)
        print(f"Total pages: {total_pages}")

        for page in range(1, total_pages + 1):
            print(f"Processing page {page}...")

            sections = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.section-details-link"))
            )

            for section in sections:
                retry_attempts = 3
                for attempt in range(retry_attempts):
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", section)
                        section.click()
                        break
                    except WebDriverException as e:
                        print(f"Retry {attempt + 1}: Element not clickable. Retrying...")
                        time.sleep(2)

                class_details = fetch_class_details(driver, subject_code)
                meeting_details = fetch_instructor_meeting_times(driver)
                enrollment_details = fetch_enrollment_details(driver)

                if class_details and meeting_details and enrollment_details:
                    combined_details = {**class_details, **meeting_details, **enrollment_details}
                    data.append(combined_details)

                close_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.ui-dialog-titlebar-close"))
                )
                close_button.click()
                time.sleep(2)

            if page < total_pages:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.paging-control.next"))
                )
                next_button.click()
                time.sleep(3)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the WebDriver
        driver.quit()

    return data

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

def save_to_s3_in_memory(df, bucket_name, s3_key):
    """Upload a Pandas DataFrame to S3 directly from memory."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue()
        )
        print(f"File uploaded to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Error uploading to S3: {e}")

def insert_data_to_snowflake_from_s3(s3_key):
    """Insert data from S3 into Snowflake, avoiding duplicates."""
    try:
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

def collect_all_data():
    all_data = []
    calls = [
        ("Spring 2025 Semester", "202530", "Computer Systems Engineering", "CSYE")
    ]

    for term, term_id, program, subject_code in calls:
        print(f"Starting data collection for: {term}, {program}, {subject_code}")
        all_data.extend(main(term, term_id, program, subject_code))

    # Save data to S3 directly and insert it into Snowflake
    if all_data:
        df = pd.DataFrame(all_data)
        s3_key = "neu_data/all_classes.csv"
        
        # Save directly to S3
        save_to_s3_in_memory(df, S3_BUCKET_NAME, s3_key)
        
        # Insert into Snowflake from S3
        insert_data_to_snowflake_from_s3(s3_key)



if __name__ == "__main__":
    collect_all_data()