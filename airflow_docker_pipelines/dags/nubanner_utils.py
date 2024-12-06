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
from io import StringIO

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
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
    """Extract instructor and meeting times with labeled classes for multiple entries."""
    try:
        instructor_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h3[@id='facultyMeetingTimes']/a"))
        )
        instructor_tab.click()

        # Wait for all meeting entries to load
        meeting_entries = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "meeting-faculty"))
        )

        instructors = []  # Collect unique instructor names
        start_date, end_date = "", ""
        timing_location_details = []  # Collect all timing and location combinations

        for idx, entry in enumerate(meeting_entries, start=1):  # Enumerate entries for labeling
            try:
                # Check if the entry is collapsible (has an accordion trigger)
                expand_button = entry.find_element(By.CLASS_NAME, "accordion-trigger")
                if expand_button.get_attribute("aria-expanded") == "false":
                    expand_button.click()
            except Exception:
                # If no accordion-trigger is found, assume the entry is expanded
                pass

            # Check if the Type is "Class"
            meeting_type_element = entry.find_element(By.XPATH, ".//div[contains(text(), 'Type:')]")
            meeting_type = meeting_type_element.text.split(":")[-1].strip()

            if meeting_type.lower() == "class":
                # Extract instructor details (if not already captured)
                if not instructors:
                    instructor_elements = entry.find_elements(By.CSS_SELECTOR, "span.meeting-faculty-member a")
                    instructors = [el.text for el in instructor_elements]

                # Extract dates (if not already captured)
                if not start_date and not end_date:
                    dates_element = entry.find_element(By.CLASS_NAME, "dates")
                    start_date, end_date = dates_element.text.split(" - ") if " - " in dates_element.text else (dates_element.text, "")

                # Extract timing and location
                timing_location_element = entry.find_element(By.CLASS_NAME, "right")
                timing_location = timing_location_element.text.strip()

                # Extract days (Class on)
                class_on_element = entry.find_element(By.CLASS_NAME, "ui-pillbox")
                class_on = class_on_element.get_attribute("title").replace("Class on: ", "").strip()


                # Combine `Class on` with `Timing and Location` and label it
                labeled_timing_location = f"Class on: {class_on} | {timing_location}"
                timing_location_details.append(labeled_timing_location)

        # Combine all instructors into a single string and join timing/location details
        instructors_str = "; ".join(set(instructors))  # Remove duplicates, if any
        timing_location_combined = " | ".join(timing_location_details)

        return {
            "instructor": instructors_str,
            "start_date": start_date.strip(),
            "end_date": end_date.strip(),
            "timing_location": timing_location_combined.strip(),
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
#S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_NAME = "neu-sa-test"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

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

def collect_data_by_semester(semester_name, calls):
    """Collect and store data for a specific semester."""
    all_data = []
    for term, term_id, program, subject_code in calls:
        print(f"Starting data collection for: {term}, {program}, {subject_code}")
        data = main(term, term_id, program, subject_code)
        if data:
            all_data.extend(data)

    # Save data to S3 for this semester
    if all_data:
        df = pd.DataFrame(all_data)
        s3_key = f"neu_data/{semester_name}_classes.csv"
        save_to_s3_in_memory(df, S3_BUCKET_NAME, s3_key)
        print(f"{semester_name} data saved to S3 at {s3_key}.")


def merge_all_semesters(file_names):
    """Merge multiple semester files into one."""
    merged_data = pd.DataFrame()
    for file_name in file_names:
        # Load each file from S3
        print(f"Loading file: {file_name}")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_name)
        semester_data = pd.read_csv(obj['Body'])
        merged_data = pd.concat([merged_data, semester_data], ignore_index=True)

    # Save merged data to S3
    merged_s3_key = "neu_data/all_classes.csv"
    save_to_s3_in_memory(merged_data, S3_BUCKET_NAME, merged_s3_key)
    print(f"Merged data saved to S3 at {merged_s3_key}.")
    return merged_s3_key