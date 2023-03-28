import json
import time
from pathlib import Path

import click
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@click.command()
@click.option('--file', help='Path to the JSONL file containing a list of community files.', required=True, type=click.Path(exists=True, dir_okay=False))
@click.option('--batch-size', default=1, help='Number of files to process in a single batch.', type=int)
@click.option('--auth', is_flag=True, help='Set this flag if already authenticated.')
def main(file, batch_size, auth):
    # Initialize Selenium WebDriver
    driver = webdriver.Chrome()

    if not auth:
        authenticate(driver)

    process_files(driver, file, batch_size)

    driver.quit()


def authenticate(driver):
    # Add the Figma authentication URL
    auth_url = "https://www.figma.com/login"
    driver.get(auth_url)

    print("Please authenticate manually and then press Enter.")
    input()


def process_files(driver, file, batch_size):
    file_path = Path(file)
    if not file_path.exists() or not file_path.is_file():
        print(f"Invalid file path: {file}")
        return

    with file_path.open() as f:
        lines = f.readlines()

    batch_start = 0
    while batch_start < len(lines):
        batch_end = batch_start + batch_size
        batch_lines = lines[batch_start:batch_end]

        for line in batch_lines:
            file_obj = json.loads(line)
            link = file_obj['link']
            copy_file(driver, link)

        batch_start = batch_end
        time.sleep(5)


def copy_file(driver, link):
    driver.get(link)

    copy_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//button[text()="Copy"]'))
    )
    copy_button.click()

    print(f"File at {link} copied to drafts.")


if __name__ == "__main__":
    main()
