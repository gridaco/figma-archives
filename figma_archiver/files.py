import os
import random
import re
import json
import sys
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv
import click
import requests
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

load_dotenv()

FIGMA_API_BASE_URL = "https://api.figma.com/v1/files"


def extract_file_key(link):
    match = re.search(r"file/([^/?]+)", link)
    return match.group(1) if match else None


def is_valid_url(url):
    return re.match(r"https?://(?:www\.)?figma\.com/.+", url)


def is_valid_json_file(file: Path):
    if file.exists():
        with open(file, "r") as output_file:
            try:
                json_data = json.load(output_file)
                if "document" in json_data:
                    return True
            except:
                return False


def save_file_locally(args):
    file_key, figma_token, output_path, validate, replace, replace_before, minify = args
    file_path = Path(output_path / f"{file_key}.json")

    if replace_before:
        # check the last modified date of the file
        if file_path.exists():
            file_mtime = os.path.getmtime(
                file_path)  # getmtime returns a float
            file_datetime = datetime.datetime.fromtimestamp(file_mtime)
            if replace_before and file_datetime < replace_before:
                file_path.unlink(missing_ok=True)
            else:
                return True

    if validate:
        # check if file exists in output_path, validate it, if valid, return
        if is_valid_json_file(file_path):
            return True

    try:
        headers = {
            "X-Figma-Token": figma_token
        }

        response = requests.get(
            f"{FIGMA_API_BASE_URL}/{file_key}", params={
                "geometry": "paths"
            }, headers=headers)

        if response.status_code == 200:
            json_data = response.json()
            if replace:
                file_path.unlink(missing_ok=True)
            with open(file_path, "w") as file:
                if not minify:
                    json.dump(json_data, file, indent=4)
                else:
                    json.dump(json_data, file, separators=(',', ':'))
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            return save_file_locally((file_key, figma_token, output_path, validate))
        else:
            return f"Failed to download file {file_key}. Error: {response.status_code}"

        if is_valid_json_file(output_path / f"{file_key}.json"):
            return True
        else:
            return f"Failed to save json file properly {file_key}. Malformed json."
    except Exception as e:
        return f"Failed to download file {file_key}. Error: {e}"


@click.command()
@click.option("-f", "--map-file", help="Path to the JSON file containing Figma file key map. (map.json)", default='../data/latest/map.json', type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-o", "--output-dir", help="Output directory to save the JSON files.", default="downloads", type=click.Path(file_okay=False))
@click.option("-c", "--concurrency", help="Number of concurrent processes.", default=cpu_count(), type=int)
@click.option('--replace', is_flag=True, help="Rather to replace the existing json file.", default=False, type=click.BOOL)
@click.option('--replace-before', required=False, help="Only replace (re-download) the file created before the date", type=click.DateTime())
@click.option('--validate', is_flag=True, help="Rather to validate the json response (downloading and already archived ones).", default=False, type=click.BOOL)
@click.option('--shuffle', is_flag=True, help="Shuffle orders.", default=False, type=click.BOOL)
@click.option('--minify', is_flag=True, help="Minify the json response with no indents, one line.", default=False, type=click.BOOL)
def main(map_file, figma_token, output_dir, concurrency, replace, replace_before, validate, shuffle, minify):
    if not figma_token:
        print(
            "Please set the FIGMA_ACCESS_TOKEN environment variable or provide it with the -t option.")
        exit(1)

    # figma token (we don't utilize multiple tokens here.)
    if figma_token.startswith("[") and figma_token.endswith("]"):
        figma_token = json.loads(figma_token)[0]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(map_file, "r") as f:
        input_data = json.load(f)

    file_links = [value for key, value in input_data.items()
                  if value and is_valid_url(value)]

    # Extract file keys from the file_links
    file_keys = [extract_file_key(link)
                 for link in file_links if extract_file_key(link)]

    existing_files = set([p.stem for p in output_path.glob("*.json")])

    if validate or replace:
        file_keys_to_download = file_keys
    else:
        file_keys_to_download = [
            file_key for file_key in file_keys if file_key not in existing_files]

    if shuffle:
        random.shuffle(file_keys_to_download)

    tqdm.write(
        f'archiving {len(file_keys_to_download)} files with {concurrency} threads with minify `{minify}` option.')
    try:
        with Pool(concurrency) as pool:
            results = list(tqdm(pool.imap_unordered(save_file_locally, [(file_key, figma_token, output_path, validate, replace, replace_before, minify) for file_key in file_keys_to_download]), total=len(
                file_keys_to_download), desc="☁️", leave=True, position=4))
    except KeyboardInterrupt:
        tqdm.write("\nInterrupted by user. Terminating...")
        pool.terminate()
        pool.join()
        sys.exit(1)

    if validate:
        for file in tqdm(output_path.glob("*.json"), desc="Validation"):
            if not is_valid_json_file(file):
                tqdm.write(
                    f"Failed to validate json file properly {file}. Malformed json. Unlinking...")
                file.unlink()

    for result in results:
        if isinstance(result, str) and result.startswith("Failed"):
            tqdm.write(result)


if __name__ == "__main__":
    main()
