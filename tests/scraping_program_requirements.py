from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import logging
import pandas as pd




def init_driver(headless=True):
    """Initialize Selenium WebDriver with optional headless mode."""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def extract_program_details(driver):
    """Extract program name and program ID."""
    program_name = None
    program_id = None

    try:
        # Extract Program Name
        program_name = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#site-title h1"))
        ).text.strip()

        # Extract Program ID
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

        # Replace em dash with comma for splitting components
        components = program_name.replace("—", ",").split(",")
        program_id_parts = [
            abbreviation_map.get(component.strip(), component.strip().upper().replace(" ", "_"))
            for component in components
        ]
        program_id = "MP_" + "_".join(program_id_parts)

    except Exception as e:
        print(f"Error extracting program details")

    return program_name, program_id

def extract_credit_hours_and_gpa(driver):
    """Extract maximum credit hours and minimum GPA from program requirements."""
    max_credit_hours = None
    min_gpa = None

    try:
        # Locate the "Program Credit/GPA Requirements" section dynamically
        try:
            # Find heading related to Credit/GPA Requirements
            credit_gpa_heading = driver.find_element(
                By.XPATH, 
                "//*[@id='programrequirementstextcontainer']//*[self::h2 or self::h3][contains(., 'Program Credit/GPA Requirements') or contains(., 'Credit/GPA Requirements')]"
            )

            # Retrieve all paragraphs following the heading
            credit_gpa_paragraphs = credit_gpa_heading.find_elements(By.XPATH, "following-sibling::p")
            for paragraph in credit_gpa_paragraphs:
                text = paragraph.text.strip()
                
                # Extract max credit hours
                if "total semester hours required" in text.lower():
                    match = re.search(r"(\d+)\s+total semester hours required", text.lower())
                    if match:
                        max_credit_hours = int(match.group(1))

                # Extract minimum GPA
                if "minimum" in text.lower() and "gpa" in text.lower():
                    gpa_match = re.search(r"minimum\s+([\d.]+)\s+gpa", text.lower())
                    if gpa_match:
                        min_gpa = float(gpa_match.group(1))
        except Exception:
            # Fallback: Search globally in the "programrequirementstextcontainer"
            try:
                container = driver.find_element(By.ID, "programrequirementstextcontainer")
                paragraphs = container.find_elements(By.XPATH, ".//p")
                for paragraph in paragraphs:
                    text = paragraph.text.strip()
                    
                    # Extract max credit hours
                    if "total semester hours required" in text.lower():
                        match = re.search(r"(\d+)\s+total semester hours required", text.lower())
                        if match:
                            max_credit_hours = int(match.group(1))

                    # Extract minimum GPA
                    if "minimum" in text.lower() and "gpa" in text.lower():
                        gpa_match = re.search(r"minimum\s+([\d.]+)\s+gpa", text.lower())
                        if gpa_match:
                            min_gpa = float(gpa_match.group(1))
            except Exception as fallback_exception:
                print("No credit hours or GPA information found in fallback search.")
    except Exception as e:
        print(f"Error extracting max credit hours or GPA")

    return max_credit_hours, min_gpa

def clean_course_code(code_text):
    """Remove unwanted characters and spaces from course codes."""
    return code_text.replace("\xa0", "").strip()

def extract_and_calculate_core_requirements(driver, program_id):
    """Extract and calculate core requirements dynamically."""
    core_courses = []
    core_courses_optional = []
    core_credit_req = 0
    core_optional_credit_req = 0

    try:
        core_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Core Requirements') or span[contains(text(), 'Core Requirements')]]/following-sibling::table[1]"))
        )
        rows = core_section.find_elements(By.XPATH, ".//tbody/tr")

        optional_section = False
        current_comment = None

        for row in rows:
            cells = row.find_elements(By.XPATH, ".//td")
            row_data = [cell.get_attribute("textContent").strip() for cell in cells]

            if len(row_data) >= 2 and row_data[0].startswith("Complete"):
                current_comment = row_data[0]
                if len(row_data) > 1 and row_data[1].isdigit():
                    core_optional_credit_req = int(row_data[1])
                optional_section = True
                continue

            if len(row_data) >= 3:
                course_code_raw = row_data[0]
                course_description = row_data[1]
                course_credit = row_data[2] if row_data[2].isdigit() else '0'

                course_codes = re.split(r"and", course_code_raw)
                course_codes = [code.strip().replace("\xa0", "") for code in course_codes]

                if "Lab" in course_description:
                    for idx, code in enumerate(course_codes):
                        credit = '0' if idx != 0 else course_credit
                        core_courses.append([program_id, code, course_description, credit, None])
                        if not optional_section and credit.isdigit() and idx == 0:
                            core_credit_req += int(credit)
                else:
                    for idx, code in enumerate(course_codes):
                        credit = course_credit if idx == 0 else '0'
                        if optional_section:
                            core_courses_optional.append([program_id, code, course_description, credit, current_comment])
                        else:
                            core_courses.append([program_id, code, course_description, credit, None])
                            if credit.isdigit():
                                core_credit_req += int(credit)

        try:
            optional_table = driver.find_element(By.XPATH, "//h2[contains(text(), 'Optional Requirements') or span[contains(text(), 'Optional Requirements')]]/following-sibling::table[1]")
            optional_rows = optional_table.find_elements(By.XPATH, ".//tbody/tr")

            for row in optional_rows:
                cells = row.find_elements(By.XPATH, ".//td")
                row_data = [cell.get_attribute("textContent").strip() for cell in cells]

                if len(row_data) >= 3:
                    course_code = row_data[0]
                    course_description = row_data[1]
                    course_credit = row_data[2] if row_data[2].isdigit() else '0'

                    core_courses_optional.append([program_id, course_code, course_description, course_credit, "Optional Requirement"])
                    if course_credit.isdigit():
                        core_optional_credit_req += int(course_credit)

        except Exception:
            pass

        return core_courses, core_courses_optional, core_credit_req, core_optional_credit_req

    except Exception as e:
        print(f"Error extracting core requirements")
        return [], [], 0, 0

def extract_subject_areas(driver, program_id):
    """
    Extract the subject areas dynamically, processing rows and ensuring comments like
    "Complete X semester hours" are properly associated with subsequent rows.
    """
    subject_areas = []
    subject_credit_req = None
    subject_notes = None
    pending_comment = None  # Store comments like "Complete X semester hours"

    

    try:
        # Locate the "General Information Systems Concentration" section
        try:
            subject_table = driver.find_element(By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table[1]")
           
        except Exception as e:
            print("[WARNING] Table not found.") 
            return subject_areas, subject_credit_req, subject_notes

        rows = subject_table.find_elements(By.XPATH, ".//tbody/tr")
        

        for i, row in enumerate(rows):
            cells = row.find_elements(By.XPATH, ".//td")
            row_data = [cell.text.strip() for cell in cells]
            

            # Case 1: "Complete X semester hours" found in the row (acts as a comment)
            if len(cells) == 2 and "Complete" in cells[0].text:
                # Capture the comment and credit hours
                pending_comment = cells[0].text.strip()
                credit_match = re.search(r"(\d+)\s+semester hours", pending_comment)
                if credit_match:
                    subject_credit_req = int(credit_match.group(1))  # Extract credit value dynamically
                
                continue  # Do not add this row as a subject area

            # Case 2: Subject code row with a comment applied
            elif len(cells) == 2:
                # Extract the subject code
                subject_code_element = row.find_element(By.XPATH, ".//td[1]/div/span")
                subject_code = subject_code_element.text.strip()

                # Add the subject code with the pending comment
                subject_areas.append([program_id, subject_code, None, subject_credit_req, pending_comment])
                

        # Extract notes
        try:
            notes_element = subject_table.find_element(By.XPATH, ".//span[@class='courselistcomment']")
            subject_notes = notes_element.text.strip()
            
        except Exception:
            print("[ERROR] No subject notes found.")  

    except Exception as e:
        print(f"[ERROR] Error extracting subject areas")  


    return subject_areas, subject_credit_req, subject_notes

def extract_electives(driver, program_id):
    """
    Extract electives dynamically from the program requirement section.
    This function handles:
    - Electives Table: Extract program_id, subject_code, and elective_subject_credit_req when there is no or one courselistcomment.
    - Electives Optional Table: Extract program_id and subject_code after the second courselistcomment is encountered.
    """
    electives = []
    electives_optional = []
    elective_subject_credit_req = None
    courselist_comment_count = 0

    try:
        # Locate the "Electives" section dynamically
        try:
            elective_heading = driver.find_element(By.XPATH,
                "//*[@id='programrequirementstextcontainer']//*[self::h2 or self::h3 or self::span][contains(., 'Electives')]"
            )
            # Locate the first table following the heading
            elective_table = elective_heading.find_element(By.XPATH, "following-sibling::table[1]")
        except Exception as e:
            print(f"[ERROR] Error locating elective section or table: {e}")
            return electives, electives_optional  # Ensure it returns empty lists

        # Parse rows inside the table
        rows = elective_table.find_elements(By.XPATH, ".//tbody/tr")

        for row in rows:
            cells = row.find_elements(By.XPATH, ".//td")

            # Case 1: Identify "courselistcomment" rows
            if len(cells) >= 2 and row.find_elements(By.XPATH, ".//span[@class='courselistcomment']"):
                courselist_comment_count += 1

                # Extract credit requirement only for the first courselistcomment
                if courselist_comment_count == 1 and elective_subject_credit_req is None:
                    try:
                        hours_cell = row.find_element(By.XPATH, ".//td[contains(@class, 'hourscol')]")
                        elective_subject_credit_req = int(hours_cell.text.strip())
                    except Exception as e:
                        print(f"[ERROR] Error extracting elective_subject_credit_req: {e}")

                continue

            # Case 2: Subject code rows
            if len(cells) == 2 and row.find_elements(By.XPATH, ".//span[@class='courselistcomment commentindent']"):
                try:
                    # Extract the subject code
                    subject_code_element = row.find_element(By.XPATH, ".//span[@class='courselistcomment commentindent']")
                    subject_code = subject_code_element.text.strip()
                    subject_code = re.sub(r"\(.*?\)", "", subject_code)  # Remove anything in parentheses

                    if courselist_comment_count > 1:
                        # After the second courselistcomment, add to electives_optional
                        electives_optional.append({
                            "program_id": program_id,
                            "subject_code": subject_code
                        })
                    else:
                        # Before the second courselistcomment, add to electives
                        electives.append({
                            "program_id": program_id,
                            "subject_code": subject_code
                        })
                except Exception as e:
                    print(f"[ERROR] Error processing subject code: {e}")
            

    except Exception as e:
        print(f"[ERROR] Error extracting electives: {e}")

    

    # Return the results
    return electives, electives_optional, elective_subject_credit_req


def extract_elective_exceptions(driver):
    """
    Extract elective exceptions from the "Electives" section of the page.
    This function looks for text within parentheses (e.g., exclusions) and handles cases like "except" or "excluded."
    """
    elective_exceptions = []

    

    try:
        # Locate the "Electives" table dynamically
        electives_table = driver.find_element(By.XPATH, "//h2[contains(text(),'Electives')]/following-sibling::table")
     

        # Find all rows in the elective table
        elective_rows = electives_table.find_elements(By.XPATH, ".//tr")
      

        for i, row in enumerate(elective_rows):
            try:
                # Look for exceptions in the comments within the table rows
                exception_span = row.find_element(By.XPATH, ".//span[contains(@class, 'courselistcomment')]")
                exception_text = exception_span.text.strip()
               

                # Extract text inside parentheses only
                if "(" in exception_text and ")" in exception_text:
                    # Extract content inside parentheses
                    exception_content = exception_text[exception_text.find("(") + 1:exception_text.find(")")]
                    
                    # Handle cases with "except" or exclusions in parentheses
                    if "except" in exception_content.lower() or "excluded" in exception_content.lower():
                        # Remove "except" or "excluded" keywords for clean output
                        exception_content = exception_content.replace("except", "").replace("excluded", "").strip()

                    # Add to the exceptions list
                    elective_exceptions.append(exception_content)
                    
            except Exception as e:
                print(f"[WARNING] Error processing row {i + 1} for elective exceptions")

    except Exception as e:
        print("[ERROR] Error retrieving elective exceptions:")

    # Combine all exceptions into a single string, if necessary
    elective_exception = "; ".join(elective_exceptions) if elective_exceptions else None
    

    return elective_exception


def export_table_to_csv(data, table_name, headers):
    """
    Export table data to a CSV file dynamically based on the table name.
    :param data: List of rows (lists or dictionaries) representing the table data.
    :param table_name: Name of the table (used for file naming).
    :param headers: List of column headers for the table.
    """
    try:
        # Convert data into a pandas DataFrame
        df = pd.DataFrame(data, columns=headers)

        # Create a filename using the table name
        filename = f"{table_name}.csv"

        # Save the DataFrame to a CSV file
        df.to_csv(filename, index=False)
        print(f"{table_name} successfully exported to {filename}")
    except Exception as e:
        print(f"Error exporting {table_name}")

if __name__ == "__main__":
    # List of URLs to parse
    urls = [
        "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis/#programrequirementstext",
        "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/data-architecture-management-ms/#programrequirementstext",
        "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/software-engineering-systems-ms/#programrequirementstext",
        "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/telecommunication-networks-ms/#programrequirementstext",
        "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/cyber-physical-systems-ms/#programrequirementstext",
        #"https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis-bridge/#programrequirementstext",
        #"https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis-bridge-online/#programrequirementstext",
        #"https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis-online/#programrequirementstext"
    ]

    # Initialize Selenium WebDriver
    driver = init_driver(headless=True)

    # Aggregated data containers
    program_requirements_data = []
    core_requirements_data = []
    core_options_requirements_data = []
    subject_areas_data = []
    electives_data = []
    electives_optional_data = []

    try:
        # Loop through each URL
        for url in urls:
            print(f"\nProcessing URL: {url}")
            driver.get(url)

            # Extract program details and all table data
            try:
                program_name, program_id = extract_program_details(driver)
                max_credit_hours, min_gpa = extract_credit_hours_and_gpa(driver)
                core_courses, core_courses_optional, core_credit_req, core_optional_credit_req = extract_and_calculate_core_requirements(driver, program_id)
                subject_areas, subject_credit_req, subject_notes = extract_subject_areas(driver, program_id)
                electives, electives_optional, elective_subject_credit_req = extract_electives(driver, program_id)
                elective_exceptions = extract_elective_exceptions(driver)

                # Append PROGRAM_REQUIREMENTS data
                program_requirements_data.append({
                    "PROGRAM_ID": program_id,
                    "MAX_CREDIT_HOURS": max_credit_hours,
                    "MIN_GPA": min_gpa,
                    "CORE_CREDIT_REQ": core_credit_req,
                    "CORE_OPTIONS_CREDIT_REQ": core_optional_credit_req,
                    "SUBJECT_CREDIT_REQ": subject_credit_req,
                    "ELECTIVE_EXCEPTION": elective_exceptions,
                    "ELECTIVE_CREDIT_REQ": elective_subject_credit_req
                })

                # Append CORE_REQUIREMENTS data
                for core_course in core_courses:
                    core_requirements_data.append({
                        "PROGRAM_ID": core_course[0],
                        "COURSE_CODE": core_course[1]
                    })

                # Append CORE_OPTIONS_REQUIREMENTS data
                for core_option in core_courses_optional:
                    core_options_requirements_data.append({
                        "PROGRAM_ID": core_option[0],
                        "COURSE_CODE": core_option[1]
                    })

                # Append SUBJECT_AREAS data
                for subject_area in subject_areas:
                    subject_areas_data.append({
                        "PROGRAM_ID": subject_area[0],
                        "SUBJECT_CODE": subject_area[1],
                        "MIN_CREDIT_HOURS": subject_area[3]
                    })

                # Append ELECTIVES data
                for elective in electives:
                    electives_data.append({
                        "PROGRAM_ID": elective["program_id"],
                        "SUBJECT_CODE": elective["subject_code"]
                    })

                # Append ELECTIVES_OPTIONAL data
                for elective_optional in electives_optional:
                    electives_optional_data.append({
                        "PROGRAM_ID": elective_optional["program_id"],
                        "SUBJECT_CODE": elective_optional["subject_code"]
                    })

            except Exception as e:
                print(f"[ERROR] Error processing URL {url}: {str(e)}")

        # Display aggregated data for all URLs
        print("\nAggregated PROGRAM_REQUIREMENTS:")
        print("PROGRAM_ID, MAX_CREDIT_HOURS, MIN_GPA, CORE_CREDIT_REQ, CORE_OPTIONS_CREDIT_REQ, SUBJECT_CREDIT_REQ, ELECTIVE_EXCEPTION, ELECTIVE_CREDIT_REQ")
        for row in program_requirements_data:
            print(f"{row['PROGRAM_ID']}, {row['MAX_CREDIT_HOURS']}, {row['MIN_GPA']}, {row['CORE_CREDIT_REQ']}, {row['CORE_OPTIONS_CREDIT_REQ']}, {row['SUBJECT_CREDIT_REQ']}, {row['ELECTIVE_EXCEPTION']}, {row['ELECTIVE_CREDIT_REQ']}")

        print("\nAggregated CORE_REQUIREMENTS:")
        print("PROGRAM_ID, COURSE_CODE")
        for row in core_requirements_data:
            print(f"{row['PROGRAM_ID']}, {row['COURSE_CODE']}")

        print("\nAggregated CORE_OPTIONS_REQUIREMENTS:")
        print("PROGRAM_ID, COURSE_CODE")
        for row in core_options_requirements_data:
            print(f"{row['PROGRAM_ID']}, {row['COURSE_CODE']}")

        print("\nAggregated SUBJECT_AREAS:")
        print("PROGRAM_ID, SUBJECT_CODE, MIN_CREDIT_HOURS")
        for row in subject_areas_data:
            print(f"{row['PROGRAM_ID']}, {row['SUBJECT_CODE']}, {row['MIN_CREDIT_HOURS']}")

        print("\nAggregated Electives:")
        print("PROGRAM_ID, SUBJECT_CODE")
        for row in electives_data:
            print(f"{row['PROGRAM_ID']}, {row['SUBJECT_CODE']}")

        print("\nAggregated Electives Optional:")
        print("PROGRAM_ID, SUBJECT_CODE")
        for row in electives_optional_data:
            print(f"{row['PROGRAM_ID']}, {row['SUBJECT_CODE']}")

    except Exception as e:
        print(f"[ERROR] Unexpected error occurred: {str(e)}")
    finally:
        driver.quit()
