import os
import re
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import click
import requests
from tqdm import tqdm

load_dotenv()

FIGMA_API_BASE_URL = "https://api.figma.com/v1/files"


def extract_file_key(link):
    match = re.search(r"file/([^/?]+)", link)
    return match.group(1) if match else None


def is_valid_url(url):
    return re.match(r"https?://(?:www\.)?figma\.com/.+", url)


@click.command()
@click.option("-f", "--figma-file-id", help="Path to the file containing Figma file IDs (one per line).", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-o", "--output-dir", help="Output directory to save the JSON files.", default="downloads", type=click.Path(file_okay=False))
def main(figma_file_id, figma_token, output_dir):
    if not figma_token:
        print("Please set the FIGMA_ACCESS_TOKEN environment variable or provide it with the -t option.")
        exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(figma_file_id, "r") as f:
        input_data = json.load(f)

    file_links = set([value for key, value in input_data.items()
                      if value and is_valid_url(value)])

    # Extract file keys from the file_links
    file_keys = [extract_file_key(link)
                 for link in file_links if extract_file_key(link)]

    existing_files = set([p.stem for p in output_path.glob("*.json")])

    with tqdm(file_keys, desc="Downloading Figma files") as progress_bar:
        for file_key in progress_bar:
            if file_key in existing_files:
                progress_bar.write(
                    f"File {file_key} already exists. Skipping...")
                continue

            save_file_locally(file_key, figma_token, output_path)

            time.sleep(1)


def save_file_locally(file, token, dir):

    headers = {
        "X-Figma-Token": token
    }

    response = requests.get(
        f"{FIGMA_API_BASE_URL}/{file}", headers=headers)

    if response.status_code == 200:
        json_data = response.json()
        with open(dir / f"{file}.json", "w") as output_file:
            json.dump(json_data, output_file, indent=4)
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 10))
        tqdm.write(
            f"Rate limit exceeded. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return save_file_locally(file, token, dir)
    else:
        tqdm.write(
            f"Failed to download file {file}. Error: {response.status_code}")


if __name__ == "__main__":
    main()
