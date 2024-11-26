from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


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
    url = "https://catalog.northeastern.edu/graduate/engineering/multidisciplinary/information-systems-msis/#programrequirementstext"
    
    # Initialize WebDriver
    driver = init_driver(headless=False)  # Change to headless=True if needed

    try:
        # Open the target page
        driver.get(url)

        # Initialize WebDriverWait
        wait = WebDriverWait(driver, 20)

        # Extract program name
        program_name = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#site-title h1"))
        ).text.strip()

        # Extract max credit hours and minimum GPA
        credit_gpa_text = driver.find_element(By.XPATH, "//h2[contains(text(),'Program Credit/GPA Requirements')]/following-sibling::p").text.strip()
        max_credit_hours = int(credit_gpa_text.split("total semester hours required")[0].strip())
        min_gpa = float(credit_gpa_text.split("Minimum")[1].strip().split("GPA")[0])

        # Extract core credit requirements
        core_credit_req_element = driver.find_element(By.XPATH, "//h2/span[contains(text(),'Core Requirements')]/ancestor::h2/following-sibling::table//td[@class='hourscol']")
        core_credit_req = int(core_credit_req_element.text.strip()) if core_credit_req_element.text.strip().isdigit() else None

        # Extract elective credit requirements
        elective_credit_req_element = driver.find_element(By.XPATH, "//h3[contains(text(),'Coursework Option')]/following-sibling::div//td[@class='hourscol']")
        elective_credit_req = int(elective_credit_req_element.text.strip()) if elective_credit_req_element.text.strip().isdigit() else None


        # Extract subject-specific requirements
        subject_credit_req = None
        try:
            # Locate the General Information Systems Concentration section
            subject_req_element = driver.find_element(
                By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table"
            )
            
            # Find the "hourscol" cell in the table
            hours_col_element = subject_req_element.find_element(By.XPATH, ".//td[@class='hourscol']")
            
            # Extract and process the text
            subject_credit_text = hours_col_element.text.strip()
            subject_credit_req = int(subject_credit_text) if subject_credit_text.isdigit() else None
        except Exception as e:
            print("Error retrieving subject-specific requirements:", e)
            subject_credit_req = None






        # Extract elective exceptions
        elective_exception = None
        try:
            elective_exception = driver.find_element(By.XPATH, "//h2[contains(text(),'Electives')]/following-sibling::table//a").text.strip()
        except Exception as e:
            print("Error retrieving elective exception:", e)

        # Extract subject-specific notes
        subject_specific_notes = None
        try:
            subject_notes_section = driver.find_element(By.XPATH, "//h2[contains(text(),'General Information Systems Concentration')]/following-sibling::table//span[@class='courselistcomment']")
            subject_specific_notes = subject_notes_section.text.strip()
        except Exception as e:
            print("Error retrieving subject-specific notes:", e)

        # Return extracted details as a dictionary
        return {
            "program_name": program_name,
            "max_credit_hours": max_credit_hours,
            "min_gpa": min_gpa,
            "core_credit_req": core_credit_req,
            "elective_credit_req": elective_credit_req,
            "subject_credit_req": subject_credit_req,
            "elective_exception": elective_exception,
            "subject_specific_notes": subject_specific_notes
        }

    finally:
        driver.quit()


if __name__ == "__main__":
    program_details = extract_program_details()
    print("Extracted Program Details:")
    for key, value in program_details.items():
        print(f"{key}: {value}")
