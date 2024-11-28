from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging


def init_driver(headless=False):
    """Initialize Selenium WebDriver with optional headless mode."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # Start browser maximized
    options.add_argument("--disable-gpu")      # Disable GPU acceleration
    options.add_argument("--no-sandbox")       # Disable sandboxing for Linux
    if headless:
        options.add_argument("--headless")     # Enable headless mode (no UI)

    # Initialize the WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def extract_program_details():
    """Extract all required program details and sections."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis/#programrequirementstext"
    #url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/data-architecture-management-ms/#programrequirementstext"
    
    # Initialize WebDriver
    driver = init_driver(headless=True)  # Use headless=True for faster execution without UI

    try:
        # Open the target page
        driver.get(url)

        # Initialize WebDriverWait
        wait = WebDriverWait(driver, 20)

        # Extract program name
        program_name = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#site-title h1"))
        ).text.strip()
        # Extract program ID (text after the comma)
        try:
            program_id = program_name.split(",")[1].strip() if "," in program_name else None
        except Exception as e:
            logging.warning("Error extracting program ID. Defaulting to None.", exc_info=e)
            program_id = None
        # Extract max credit hours and minimum GPA
        try:
            credit_gpa_text = driver.find_element(By.XPATH, "//h2[contains(text(),'Program Credit/GPA Requirements')]/following-sibling::p").text.strip()
            max_credit_hours = int(credit_gpa_text.split("total semester hours required")[0].strip())
            min_gpa = float(credit_gpa_text.split("Minimum")[1].strip().split("GPA")[0])
            
        except Exception as e:
            print("Error extracting max credit hours or GPA:", e)
            max_credit_hours = None
            min_gpa = None

        # Extract core courses
        core_courses = []
        try:
            core_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[1]/tbody")
            core_rows = core_table.find_elements(By.XPATH, "./tr")
            for row in core_rows:
                course_codes = []
                course_title = None

                # Handle multiple course codes in a single row
                try:
                    course_code_elements = row.find_elements(By.XPATH, "./td[1]//a")  # Match both direct and nested <a> tags
                    course_codes = [code.text.strip() for code in course_code_elements if code.text.strip()]
                except Exception:
                    logging.warning("No course codes found for a core course row.")

                # Extract course title
                try:
                    course_title = row.find_element(By.XPATH, "./td[2]").text.strip()
                except Exception:
                    course_title = "No course title"

                # Append if valid course information is found
                if course_codes or course_title:
                    core_courses.append({"course_codes": course_codes, "course_title": course_title})
        except Exception as e:
            logging.warning(f"Error extracting core courses: {e}")

        # Extract elective courses
        elective_courses = []
        try:
            elective_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[3]/tbody")
            elective_rows = elective_table.find_elements(By.XPATH, "./tr")
            for row in elective_rows:
                try:
                    # Extract course or subject text
                    course_title_element = row.find_element(By.XPATH, "./td[1]/div/span")
                    course_title = course_title_element.text.strip()
                    
                    # Remove text in parentheses (e.g., "(except CSYE 6220)")
                    if "(" in course_title and ")" in course_title:
                        course_title = course_title.split("(")[0].strip()  # Keep only the part before the parentheses
                    
                    elective_courses.append(course_title)
                except Exception:
                    logging.warning("Error extracting an elective course.")
        except Exception as e:
            logging.warning(f"Error extracting elective courses: {e}")

####
        try:
            subject_element = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[2]/tbody/tr[2]/td[1]/div/span")
            subject_text = subject_element.text.strip()
            #subject_credit_reqq = int(subject_credit_text) if subject_credit_text.isdigit() else 0  # Default to 0 if not a digit
        except Exception as e:
            logging.warning("Error retrieving subject-specific requirements. Defaulting to 0.", exc_info=e)
            
####
        # Extract subject-specific requirements
        subject_credit_req = 0
        try:
            subject_req_element = driver.find_element(
                By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table"
            )
            hours_col_element = subject_req_element.find_element(By.XPATH, ".//td[@class='hourscol']")
            subject_credit_text = hours_col_element.text.strip()
            subject_credit_req = int(subject_credit_text) if subject_credit_text.isdigit() else None
        except Exception as e:
            logging.warning("Error retrieving subject-specific requirements:", exc_info=e)

        # Extract elective exceptions
        elective_exception = None
        try:
            elective_exception = driver.find_element(By.XPATH, "//h2[contains(text(),'Electives')]/following-sibling::table//a").text.strip()
        except Exception as e:
            logging.warning("Error retrieving elective exception:", exc_info=e)

        # Extract subject-specific notes
        subject_specific_notes = None
        try:
            subject_notes_section = driver.find_element(By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table//span[@class='courselistcomment']")
            subject_specific_notes = subject_notes_section.text.strip()
        except Exception as e:
            logging.warning("Error retrieving subject-specific notes:", exc_info=e)

        # Extract core credit requirement by summing the values in td[3]
        core_credit_req = 0
        try:
            core_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[1]/tbody")
            core_rows = core_table.find_elements(By.XPATH, "./tr")
            for row in core_rows:
                try:
                    # Extract the credit value from the third column
                    credit_element = row.find_element(By.XPATH, "./td[3]")
                    credit_value = int(credit_element.text.strip())
                    core_credit_req += credit_value  # Sum up the credit values
                except Exception as e:
                    logging.warning(f"Error extracting credit value for a row: {e}")
        except Exception as e:
            logging.warning(f"Error locating core courses table: {e}")

        #return core_credit_req
        elective_credit_req = max_credit_hours - core_credit_req - subject_credit_req

        # Return extracted details as a dictionary
        return {
            "program_name": program_name,

            "PROGRAM_REQUIREMENTS "
            "program_id": program_id,
            "max_credit_hours": max_credit_hours,
            "min_gpa": min_gpa,
            "core_credit_req": core_credit_req,
            "elective_credit_req": elective_credit_req,
            "subject_credit_req": subject_credit_req,
            "elective_exception": elective_exception,

            "SUBJECT_AREAS "
            "program_id": program_id,
            "subject_code": subject_text,
            "min_credit_hours": subject_credit_req,
            "notes": subject_specific_notes,

            "core_requirements "
            "program_id": program_id,
            "core_courses": core_courses,
          
            "elective_requirements "
            "program_id": program_id,
            "elective_courses": elective_courses,
            "subject_credit_req": subject_credit_req,
           
          
            
            
            
            
            
        }

        
    finally:
        driver.quit()


if __name__ == "__main__":
    program_details = extract_program_details()
    print("Extracted Program Details:")
    for key, value in program_details.items():
        if key == "core_courses":         
            for course in value:
                print(f"{key} : {', '.join(course['course_codes'])}")
                
        elif key == "elective_courses":
            print(f"{key}: {', '.join(value)}")
        else:
            print(f"{key}: {value}")
