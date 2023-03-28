import json
import math
import os
import random
from dotenv import load_dotenv
import time
from pathlib import Path

import click
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm


err_timeout_code = 'timeout'

progress_bar = None

load_dotenv()

credentials = {
    "email": os.getenv("FIGMA_EMAIL"),
    "password": os.getenv("FIGMA_PASSWORD"),
}

# ensure credentials are set
if not credentials['email'] or not credentials['password']:
    tqdm.write(
        "Please set the FIGMA_EMAIL and FIGMA_PASSWORD environment variables.")
    exit(1)

progress_file = f"./progress/{credentials['email']}.copies.json"


def load_progress():
    if not Path(progress_file).is_file():
        return {}

    with open(progress_file, 'r') as f:
        progress = json.load(f)

    return progress


def save_progress(progress):
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=4)


def remove_duplicates(file, progress):
    file_path = Path(file)
    if not file_path.exists() or not file_path.is_file():
        tqdm.write(f"Invalid file path: {file}")
        return

    with file_path.open() as f:
        lines = f.readlines()

    # Remove duplicates by checking if the link is in progress
    unique_lines = [line for line in lines if json.loads(line)[
        'link'] not in progress]
    return unique_lines


def authenticate(driver):
    email = credentials['email']
    password = credentials['password']

    # Add the Figma authentication URL
    auth_url = "https://www.figma.com/login"
    driver.get(auth_url)

    # Locate and fill in the email input field
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//form/input[@name="email"]'))
    )
    email_input.clear()
    email_input.send_keys(email)

    # Locate and fill in the password input field
    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//form/input[@name="password"]'))
    )
    password_input.clear()
    password_input.send_keys(password)

    # wait a sec
    time.sleep(1)

    # Locate and click the submit button
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//form/button[@type="submit"]'))
    )
    submit_button.click()

    # wait for server to respond with cookies (wait until redirect to dashboard)
    # the dashboard url is https://www.figma.com/files/recent?xxxxx
    WebDriverWait(driver, 10).until(
        EC.url_matches(r"https://www.figma.com/files/recent\?*")
    )

    return True

def get_driver_options():
    chrome_options = Options()

    # Disable images
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    # Disable CSS
    chrome_options.add_argument("--disable-web-resources")

    # Other options to improve performance
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-notifications")
    # chrome_options.add_argument("--disable-gpu") - removed cuz figma uses webgl and page fails if gpu is disabled
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument('--disable-smooth-scrolling')


    return chrome_options


@click.command()
@click.option('--file', help='Path to the JSONL file containing a list of community files.', required=True, type=click.Path(exists=True, dir_okay=False))
@click.option('--batch-size', default=1, help='Number of files to process in a single batch.', type=int)
def main(file, batch_size):
    # Initialize Selenium WebDriver
    chrome_options = get_driver_options()
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "none" # this disables waiting for page load
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options, desired_capabilities=caps)


    try:
        progress = load_progress()
        lines = remove_duplicates(file, progress)

        # intial authentication
        authenticate(driver)

        # Initialize the progress bar
        global progress_bar
        progress_bar = tqdm(total=len(lines))

        process_files(driver, lines, batch_size, progress)

    except KeyboardInterrupt:
        tqdm.write("\nInterrupted by user. Exiting...")
    finally:
        driver.quit()



# Add the progress parameter to process_files

def process_files(driver, lines, batch_size, progress):
    processed_count = 0
    for line in lines:
        if processed_count >= batch_size:
            break

        file_obj = json.loads(line)
        link = file_obj['link']

        result = copy_file(driver, link)
        if not result is False:
            # result is a newly copied file url. save it.
            progress[link] = result
            save_progress(progress)
            processed_count += 1

        global progress_bar
        progress_bar.update(1)

        # time.sleep(random.uniform(0.5, 1.5))


def copy_file(driver, link, max_retries=3):

    # sometimes the page takes a while to load, throw a timeout exception.
    retries = 0
    while retries < max_retries:
        try:
            tqdm.write(f"Copying file at {link} to drafts...")
            driver.get(link)
            break
        except TimeoutException:
            retries += 1
            tqdm.write(f"TimeoutException encountered. Retrying {retries}/{max_retries}...")
            if retries == max_retries:
                tqdm.write(f"Failed to load {link} after {max_retries} retries. Skipping...")
                return err_timeout_code
            time.sleep(1)


    time.sleep(0.5)  # Add a short sleep duration before locating the button

    tqdm.write(f"Locating the copy button...")
    try:
        copy_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, '//button/div[contains(text(), "Get a copy")]'))
        )
        tqdm.write(f"'Get a Copy' button located")
    except:
        # this could be beause the file is a paid file
        tqdm.write(f"Unable to locate the copy button. Skipping...")
        return
    
    # Click the copy button
    try:
        copy_button.click()
    except StaleElementReferenceException:
        tqdm.write(f"StaleElementReferenceException encountered. Retrying...")
        return copy_file(driver, link)

    # Check for the presence of the authentication iframe
    try:
        auth_iframe = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "figma-auth-iframe"))
        )

        # If the iframe is found, proceed with authentication
        if auth_iframe:
            authenticate(driver)
            # the authenticate function will redirect to the file page. So, call the copy_file function again
            return copy_file(driver, link)

    except TimeoutException:
        # If the iframe is not found, assume the user is authenticated
        tqdm.write(f"File at {link} copied to drafts.")

    try:
        # After copying the file, the site will open new tab to the drafted file page. read the url and save it for later
        # Wait until the site opens the new tab
        WebDriverWait(driver, 10).until(
            EC.number_of_windows_to_be(2)
        )

        # focus on the new tab
        driver.switch_to.window(driver.window_handles[1])
        # read the url
        current_url = driver.current_url
        # close the new tab (only new tab) and switch back to the original tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        # if it's same as the link, then it's considered failed
        if current_url == link:
            tqdm.write(f"Failed to copy the file at {link}")
            return False
        else:
            tqdm.write(f"Current URL after copying the file: {current_url}")
            return current_url
    except:
        tqdm.write(f"Failed to copy the file at {link}")
        return False



if __name__ == "__main__":
    main()
