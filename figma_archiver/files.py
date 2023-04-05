import os
import re
import json
import sys
import time
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
    file_key, figma_token, output_path, validate, minify = args
    headers = {
        "X-Figma-Token": figma_token
    }

    if validate:
        # check if file exists in output_path, validate it, if valid, return
        if is_valid_json_file(output_path / f"{file_key}.json"):
           return True

    try:
        response = requests.get(
            f"{FIGMA_API_BASE_URL}/{file_key}", params={
                "geometry": "paths"
            }, headers=headers)

        if response.status_code == 200:
            json_data = response.json()
            with open(output_path / f"{file_key}.json", "w") as output_file:
                if minify:
                    json.dump(json_data, output_file, separators=(',', ':'))
                else:
                    json.dump(json_data, output_file, indent=4)
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
@click.option("-f", "--figma-file-id", help="Path to the JSON file containing Figma file IDs.", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-o", "--output-dir", help="Output directory to save the JSON files.", default="downloads", type=click.Path(file_okay=False))
@click.option("-c", "--concurrency", help="Number of concurrent processes.", default=cpu_count(), type=int)
@click.option('--validate', is_flag=True, help="Rather to validate the json response (downloading and already archived ones).", default=False, type=click.BOOL)
@click.option('--minify', is_flag=True, help="Minify the json response with no indents, one line.", default=True, type=click.BOOL)
def main(figma_file_id, figma_token, output_dir, concurrency, validate, minify):
    if not figma_token:
        print(
            "Please set the FIGMA_ACCESS_TOKEN environment variable or provide it with the -t option.")
        exit(1)
    
    # figma token (we don't utilize multiple tokens here.)
    if figma_token.startswith("[") and figma_token.endswith("]"):
      figma_token = json.loads(figma_token)[0]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(figma_file_id, "r") as f:
        input_data = json.load(f)

    file_links = [value for key, value in input_data.items()
                  if value and is_valid_url(value)]

    # Extract file keys from the file_links
    file_keys = [extract_file_key(link)
                 for link in file_links if extract_file_key(link)]

    existing_files = set([p.stem for p in output_path.glob("*.json")])

    if validate:
      file_keys_to_download = file_keys
    else:
      file_keys_to_download = [
          file_key for file_key in file_keys if file_key not in existing_files]

    tqdm.write(
        f'archiving {len(file_keys_to_download)} files with {concurrency} processes')
    try:
        with Pool(concurrency) as pool:
            results = list(tqdm(pool.imap_unordered(save_file_locally, [(file_key, figma_token, output_path, validate, minify) for file_key in file_keys_to_download]), total=len(
                file_keys_to_download), desc="Downloading Figma files"))
    except KeyboardInterrupt:
        tqdm.write("\nInterrupted by user. Terminating...")
        pool.terminate()
        pool.join()
        sys.exit(1)
    
    if validate:
      for file in tqdm(output_path.glob("*.json"), desc="Validation"):
          if not is_valid_json_file(file):
            tqdm.write(f"Failed to validate json file properly {file}. Malformed json. Unlinking...")
            file.unlink()

    for result in results:
        if isinstance(result, str) and result.startswith("Failed"):
            tqdm.write(result)


if __name__ == "__main__":
    main()
