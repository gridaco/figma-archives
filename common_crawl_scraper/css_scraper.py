import os
import re
from concurrent.futures import ThreadPoolExecutor

import chardet
import requests
from bs4 import BeautifulSoup

input_folder = 'YOUR_INPUT_FOLDER' # change it
output_folder = os.path.join(input_folder, 'downloaded_css')

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Function to download CSS file
def download_css(url, file_name):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_name, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Downloaded: {file_name}")
    except:
        print(f"Failed to download: {url}")

# Function to process an HTML file
def process_file(file):
    if file.endswith('.html'):
        file_path = os.path.join(input_folder, file)

        # Detect file encoding
        with open(file_path, 'rb') as raw_file:
            result = chardet.detect(raw_file.read())
        file_encoding = result['encoding']

        # Read the first line for the URL
        with open(file_path, 'r', encoding=file_encoding, errors='ignore') as html_file:
            first_line = html_file.readline().strip()
            base_url = re.sub(r"<!-- (.*) -->", r"\1", first_line).rstrip("/")

        # Read the file with the detected encoding for parsing
        with open(file_path, 'r', encoding=file_encoding, errors='ignore') as html_file:
            soup = BeautifulSoup(html_file, 'html.parser')

            # Find all the CSS links
            css_links = soup.find_all('link', rel='stylesheet', href=True)
            css_urls = [link['href'] for link in css_links]

            # Download the CSS files
            for css_url in css_urls:
                if not css_url.startswith('http'):
                    css_url = base_url + css_url
                css_name = f"{file}-{css_url.split('/')[-1]}"
                output_file_path = os.path.join(output_folder, css_name)
                download_css(css_url, output_file_path)

            # Save inline CSS content as a separate file
            inline_css_tags = soup.find_all('style', type='text/css')
            for idx, inline_css_tag in enumerate(inline_css_tags):
                inline_css_content = inline_css_tag.string
                if inline_css_content:
                    css_name = f"{file}-inline-{idx}.css"
                    output_file_path = os.path.join(output_folder, css_name)
                    with open(output_file_path, 'w', encoding='utf-8') as inline_css_file:
                        inline_css_file.write(inline_css_content)

# Iterate through the HTML files using multithreading
with ThreadPoolExecutor() as executor:
    executor.map(process_file, os.listdir(input_folder))
