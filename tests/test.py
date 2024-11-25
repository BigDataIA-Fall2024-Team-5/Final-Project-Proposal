from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def init_driver():
    """Initialize Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # Open browser in maximized mode
    driver = webdriver.Chrome(options=options)  # Ensure ChromeDriver is in PATH
    return driver

def fetch_class_details(driver):
    """Extract class details."""
    try:
        # Wait for the parent section to load
        popup_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section[aria-labelledby='classDetails']"))
        )

        # Extract text from the entire section and parse it manually
        section_text = popup_section.text

        # Parse text-based fields (those separated by newlines)
        details = {
            "Associated Term": section_text.split("Associated Term:")[1].split("\n")[0].strip(),
            "CRN": popup_section.find_element(By.ID, "courseReferenceNumber").text.strip(),
            "Campus": section_text.split("Campus:")[1].split("\n")[0].strip(),
            "Schedule Type": section_text.split("Schedule Type:")[1].split("\n")[0].strip(),
            "Instructional Method": section_text.split("Instructional Method:")[1].split("\n")[0].strip(),
            "Section Number": popup_section.find_element(By.ID, "sectionNumber").text.strip(),
            "Course Number": popup_section.find_element(By.ID, "courseNumber").text.strip(),
            "Title": popup_section.find_element(By.ID, "courseTitle").text.strip(),
            "Credit Hours": section_text.split("Credit Hours:")[1].split("\n")[0].strip(),
        }

        # Print details in desired format
        print("\nClass Details:")
        for key, value in details.items():
            print(f"{key}: {value}")

        return details

    except Exception as e:
        print(f"Error fetching class details: {e}")
        return {}



def fetch_instructor_meeting_times(driver):
    """Extract instructor and meeting times."""
    try:
        # Click on "Instructor/Meeting Times"
        instructor_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h3[@id='facultyMeetingTimes']/a"))
        )
        instructor_tab.click()

        # Wait for the content to load
        meeting_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "meeting-faculty"))
        )
        instructors = [
            element.text for element in meeting_content.find_elements(By.CSS_SELECTOR, "span.meeting-faculty-member a")
        ]
        meeting_times = meeting_content.find_element(By.CLASS_NAME, "ui-pillbox-summary").text
        dates = meeting_content.find_element(By.CLASS_NAME, "dates").text
        location = meeting_content.find_element(By.CLASS_NAME, "right").text

        return {
            "Instructors": instructors,
            "Meeting Times": meeting_times,
            "Dates": dates,
            "Location": location,
        }
    except Exception as e:
        print(f"Error fetching instructor/meeting times: {e}")
        return {}


def main():
    driver = init_driver()

    try:
        # Open the starting link
        driver.get("https://nubanner.neu.edu/StudentRegistrationSsb/ssb/registration/registration")
        print("Page loaded.")

        # Click on "Browse Classes"
        browse_classes_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "classSearchLink"))
        )
        browse_classes_link.click()
        print("Navigated to Browse Classes.")

        # Select "Spring 2025 Semester"
        term_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "select2-choice"))
        )
        term_dropdown.click()

        term_search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "s2id_autogen1_search"))
        )
        term_search_input.send_keys("Spring 2025 Semester")
        time.sleep(2)

        matching_term = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='202530']"))
        )
        matching_term.click()

        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "term-go"))
        )
        continue_button.click()

        # Search for "Information Systems Program"
        subject_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.select2-choices input.select2-input"))
        )
        subject_input.send_keys("Information Systems Program")
        time.sleep(2)

        matching_subject = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='INFO']"))
        )
        matching_subject.click()

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "search-go"))
        )
        search_button.click()
        print("Search completed.")

        # Process each class in the search results
        sections = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.section-details-link"))
        )

        for index, section in enumerate(sections[:5]):  # Limit to 5 classes
            print(f"\nProcessing class {index + 1}...")
            section.click()

            # Fetch class details
            class_details = fetch_class_details(driver)
            print(f"Class Details: {class_details}")

            # Fetch instructor and meeting times
            meeting_details = fetch_instructor_meeting_times(driver)
            print(f"Instructor/Meeting Times: {meeting_details}")

            # Close the popup
            close_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.ui-dialog-titlebar-close"))
            )
            close_button.click()
            time.sleep(2)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
