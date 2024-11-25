from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-gpu")  # Disable GPU rendering
    chrome_options.add_argument("--window-size=1920,1080")  # Optional: set window size

    service = Service("/usr/local/bin/chromedriver")  # Explicitly set the path to ChromeDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Initialize the driver
driver = init_driver()

try:
    # Open the target URL
    driver.get("https://nubanner.neu.edu/StudentRegistrationSsb/ssb/classSearch")

    # Interact with the dropdown
    subject_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.select2-choices input.select2-input"))
    )
    subject_input.send_keys("Information Systems Program")
    time.sleep(2)

    # Select the first option
    first_option = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "li.select2-result"))
    )
    first_option.click()

    # Click the search button
    search_button = driver.find_element(By.ID, "search-go")
    search_button.click()

    # Wait for the results page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.section-details-link"))
    )
    print("Results page loaded.")

    # Extract and print results (e.g., section details)
    sections = driver.find_elements(By.CSS_SELECTOR, "a.section-details-link")
    for section in sections:
        print(f"Found Section: {section.text}")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()
