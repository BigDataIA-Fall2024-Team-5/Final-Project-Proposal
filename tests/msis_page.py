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
    #url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis/#programrequirementstext"
    #url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/data-architecture-management-ms/#programrequirementstext"
    url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/software-engineering-systems-ms/#programrequirementstext"

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


        
        # Extract core courses dynamically
        core_courses = []
        try:
            # Attempt to locate the 'Core Requirements' heading dynamically
            try:
                core_heading = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']//h2[contains(text(), 'Core Requirements')]")
                # Find the table immediately following the 'Core Requirements' heading
                core_table = core_heading.find_element(By.XPATH, "following-sibling::table[1]/tbody")
            except Exception:
                # If 'Core Requirements' heading is not found, fall back to the first table in the container
                core_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[1]/tbody")

            # Get all rows from the identified table
            core_rows = core_table.find_elements(By.XPATH, "./tr")
            for row in core_rows:
                # Handle multiple course codes in a single row
                try:
                    course_code_elements = row.find_elements(By.XPATH, "./td[1]//a")  # Match nested <a> tags
                    course_codes = [code.text.strip() for code in course_code_elements if code.text.strip()]
                    if course_codes:
                        core_courses.extend(course_codes)  # Add course codes directly to the list
                except Exception:
                    logging.warning("No course codes found for a core course row.")
        except Exception as e:
            logging.warning(f"Error extracting core courses: {e}")


        # Extract core credit requirement 
        core_credit_req = 0
        try:
            # Attempt to locate the 'Core Requirements' heading dynamically
            try:
                core_heading = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']//h2[contains(text(), 'Core Requirements')]")
                # Find the table immediately following the 'Core Requirements' heading
                core_table = core_heading.find_element(By.XPATH, "following-sibling::table[1]/tbody")
            except Exception:
                # If 'Core Requirements' heading is not found, fall back to the first table in the container
                core_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']/table[1]/tbody")

            # Get all rows from the identified table
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
            logging.warning(f"Error locating or processing the core courses table: {e}")


        # Extract elective courses dynamically
        elective_courses = []
        try:
            # Locate the 'Electives' heading dynamically
            elective_heading = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']//h2[contains(text(), 'Electives')]")
            
            # Find the table immediately following the 'Electives' heading
            elective_table = elective_heading.find_element(By.XPATH, "following-sibling::table[1]/tbody")
            
            # Get all rows from the identified table
            elective_rows = elective_table.find_elements(By.XPATH, "./tr")
            
            # Process each row in the table
            for row in elective_rows:
                try:
                    # Extract course or subject text from the row
                    course_title_element = row.find_element(By.XPATH, "./td[1]/div/span")
                    course_title = course_title_element.text.strip()

                    # Check for nested <a> tags and extract their text if present
                    course_link_element = course_title_element.find_elements(By.TAG_NAME, "a")
                    if course_link_element:
                        course_title = course_link_element[0].text.strip()

                    # Remove text in parentheses (e.g., "(except CSYE 6220)")
                    if "(" in course_title and ")" in course_title:
                        course_title = course_title.split("(")[0].strip()

                    # Append the cleaned course title to the elective courses list
                    elective_courses.append(course_title)
                except Exception as row_ex:
                    logging.warning(f"Error extracting course from row: {row_ex}")
        except Exception as e:
            logging.warning(f"Error locating or extracting elective courses: {e}")

        # Extract max credit hours and minimum GPA
        max_credit_hours = None
        min_gpa = None

        try:
            # Locate the "Program Credit/GPA Requirements" heading dynamically
            try:
                # Search for the heading
                credit_gpa_heading = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']//h2[contains(text(), 'Program Credit/GPA Requirements') or contains(text(), 'Credit/GPA Requirements')]")

                # Check for all <p> tags following the heading
                credit_gpa_paragraphs = credit_gpa_heading.find_elements(By.XPATH, "following-sibling::p")
                for paragraph in credit_gpa_paragraphs:
                    text = paragraph.text.strip()
                    # Extract max credit hours
                    if "total semester hours required" in text:
                        max_credit_hours = int(text.split("total semester hours required")[0].strip())
                    # Extract min GPA
                    if "Minimum" in text and "GPA" in text:
                        min_gpa = float(text.split("Minimum")[1].strip().split("GPA")[0])

            except Exception:
                # Fallback: Search for all relevant <p> tags globally in the container
                try:
                    container = driver.find_element(By.ID, "programrequirementstextcontainer")
                    paragraphs = container.find_elements(By.XPATH, ".//p")
                    for paragraph in paragraphs:
                        text = paragraph.text.strip()
                        if "total semester hours required" in text:
                            max_credit_hours = int(text.split("total semester hours required")[0].strip())
                        if "Minimum" in text and "GPA" in text:
                            min_gpa = float(text.split("Minimum")[1].strip().split("GPA")[0])
                except Exception:
                    logging.warning("No credit hours or GPA information found.")

        except Exception as e:
            logging.error(f"Error extracting max credit hours or GPA: {e}")


        # Extract subject-specific requirements
        subject_credit_req = None  # Default to None if not found
        try:
            # Locate the section dynamically
            subject_req_element = driver.find_element(
                By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table"
            )
            
            # Extract the value from the 'hourscol' column
            hours_col_element = subject_req_element.find_element(By.XPATH, ".//td[@class='hourscol']")
            subject_credit_text = hours_col_element.text.strip()

            # Convert the extracted text to an integer if it is a valid digit
            subject_credit_req = int(subject_credit_text) if subject_credit_text.isdigit() else None

        except Exception as e:
            # Log a warning if the section is not present
            logging.warning("General Information Systems Concentration not present")
            logging.warning(f"Details: {e}")
        
        # Extract subject-specific notes
        subject_specific_notes = None  # Default to None if not found
        try:
            # Locate the section dynamically
            subject_notes_section = driver.find_element(
                By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table//span[@class='courselistcomment']"
            )
            
            # Extract the text from the located element
            subject_specific_notes = subject_notes_section.text.strip()

            # Remove any colons from the extracted text
            if ":" in subject_specific_notes:
                subject_specific_notes = subject_specific_notes.replace(":", "")

        except Exception as e:
            # Log a warning if the section is not present
            logging.warning("General Information Systems Concentration notes not present")
            logging.warning(f"Details: {e}")

        # Extract elective exceptions
        elective_exceptions = []
        try:
            # Locate the "Electives" heading dynamically
            electives_table = driver.find_element(By.XPATH, "//h2[contains(text(),'Electives')]/following-sibling::table")

            # Find all rows in the elective table
            elective_rows = electives_table.find_elements(By.XPATH, ".//tr")

            for row in elective_rows:
                try:
                    # Look for exceptions in the comments within the table rows
                    exception_span = row.find_element(By.XPATH, ".//span[contains(@class, 'courselistcomment')]")
                    exception_text = exception_span.text.strip()

                    # Extract text inside parentheses only
                    if "(" in exception_text and ")" in exception_text:
                        # Extract content inside parentheses
                        exception_content = exception_text[exception_text.find("(") + 1:exception_text.find(")")]
                        
                        # Handle cases with "except" or exclusions in parentheses
                        if "except" in exception_content or "excluded" in exception_content:
                            # Remove "except" or "excluded" keywords for clean output
                            exception_content = exception_content.replace("except", "").replace("excluded", "").strip()

                        # Add to the exceptions list
                        elective_exceptions.append(exception_content)
                except Exception as e:
                    logging.warning(f"Error processing row for elective exceptions: {e}")

        except Exception as e:
            logging.warning("Error retrieving elective exceptions:", exc_info=e)

        # Combine all exceptions into a single string, if necessary
        if elective_exceptions:
            elective_exception = "; ".join(elective_exceptions)
        else:
            elective_exception = None

              
        # Extract program ID
        try:
            # Define a mapping of keywords to abbreviations
            abbreviation_map = {
                "Master of Science": "MS",
                "MS": "MS",
                "Graduate Certificate": "CERT",
                "Information Systems": "IS",
                "Cyber-Physical Systems": "CPS",
                "Data Architecture and Management": "DAM",
                "Software Engineering Systems": "SES",
                "Telecommunication Networks": "TN",
                "Broadband Wireless Systems": "BW",
                "Engineering Leadership": "EL",
                "Blockchain and Smart Contract Engineering": "BC_SC",
                "IP Telephony Systems": "IPT",
            }

            # Split the program name into components
            components = program_name.replace("—", ",").split(",")  # Replace em dash with comma
            program_id_parts = []

            for component in components:
                # Clean up the component
                component = component.strip()

                # Look up the abbreviation or keep as-is if no mapping exists
                abbreviation = abbreviation_map.get(component, component.upper().replace(" ", "_"))
                program_id_parts.append(abbreviation)

            # Combine the parts into the final program ID
            program_id = "MP_" + "_".join(program_id_parts)

        except Exception as e:
            logging.warning("Error extracting program ID. Defaulting to None.", exc_info=e)
            program_id = None

        # Extract subject for the corses dynamically
        subject_text = None  # Default to None if not found
        try:
            # Locate the second table under the program requirement container dynamically
            subject_table = driver.find_element(By.XPATH, "//*[@id='programrequirementstextcontainer']//table[2]")

            # Locate the specific row or span containing the subject information
            subject_row = subject_table.find_element(By.XPATH, ".//tr[contains(@class, 'lastrow')]//span[contains(@class, 'courselistcomment')]")
            subject_text = subject_row.text.strip() if subject_row.text.strip() else None

        except Exception as e:
            # Log a warning if the subject-specific information is not present
            logging.warning("Error retrieving subject-specific requirements. Defaulting to None.", exc_info=e)

        # Log or print the result
        print(f"Subject Text: {subject_text}")

        # Calculate elective_credit_req
        elective_credit_req = None  # Default to None if calculation cannot be performed
        try:
            # Ensure subject_credit_req is treated as 0 if it is None
            subject_credit_req = subject_credit_req if subject_credit_req is not None else 0

            # Perform the calculation only if max_credit_hours and core_credit_req are valid
            if max_credit_hours is not None and core_credit_req is not None:
                elective_credit_req = max_credit_hours - core_credit_req - subject_credit_req
            else:
                logging.warning("Cannot calculate elective_credit_req due to missing core or max credit hours.")
        except Exception as e:
            logging.error(f"Error calculating elective_credit_req: {e}")

        
        # Print the final sheet
        print("\n------------------Final Sheet--------------------\n")
        print(f"program_name: {program_name}\n")

        print("\n PROGRAM_REQUIREMENTS \n")
        print(f"program_id: {program_id}")
        print(f"max_credit_hours: {max_credit_hours}")
        print(f"min_gpa: {min_gpa}")
        print(f"core_credit_req: {core_credit_req}")
        print(f"elective_credit_req: {elective_credit_req}")
        print(f"subject_credit_req: {subject_credit_req}")
        print(f"elective_exception: {elective_exception}\n")

        print("\n SUBJECT_AREAS \n")
        print(f"program_id: {program_id}")
        print(f"subject_code: {subject_text}")
        print(f"min_credit_hours: {subject_credit_req}")
        print(f"notes: {subject_specific_notes}\n")

        print("\n core_requirements \n")
        print(f"program_id: {program_id}")
        print(f"core_courses: {core_courses}\n")
        print(f"core_credit_req: {core_credit_req}\n")

        print("\n elective_requirements \n")
        print(f"program_id: {program_id}")
        print(f"elective_courses: {elective_courses}")
        print(f"elective_credit_req: {elective_credit_req}\n \n")

        # Return extracted details as a dictionary
        return {
            "program_name": program_name,
            "core_courses": core_courses,
            "core_credit_req": core_credit_req,
            "elective_courses": elective_courses,
            "max_credit_hours": max_credit_hours,
            "min_gpa": min_gpa,
            "subject_credit_req": subject_credit_req,
            "subject_specific_notes": subject_specific_notes,
            "elective_exception": elective_exception,
            "program_id": program_id,
            "elective_credit_req": elective_credit_req,          
            }
        
        
    finally:
        driver.quit()


if __name__ == "__main__":
    program_details = extract_program_details()
    print("Extracted Program Details:")
    for key, value in program_details.items():
        if key == "core_courses":
            # Convert the list of core courses to a comma-separated string before printing
            print(f"{key}: {', '.join(value)}")
        elif key == "elective_courses":
            # Convert the list of elective courses to a comma-separated string before printing
            print(f"{key}: {', '.join(value)}")
        else:
            # For other keys, print the value as is
            print(f"{key}: {value}")

