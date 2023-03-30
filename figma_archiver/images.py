import glob
import logging
import click
import time
import json
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import backoff
from ssl import SSLError
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import chain

load_dotenv()

API_BASE_URL = "https://api.figma.com/v1"


def read_file_data(file_key):
    with open(os.path.join(file_key, f"{file_key}.json")) as f:
        return json.load(f)



def get_node_ids(data, depth=None, skip_canvas=True):
    """

    In most cases, you want to set depth to 1 or None with skip_canvas=True.

    depth:
     - None means no limit
     - 0 means no nodes, retrurns only canvas ids (if skip_canvas is False) otherwise empty list
     - 1 means only canvas ids (if skip_canvas is False) and direct children of canvas

    ...
    """
    def extract_ids_recursively(node, current_depth):
        if depth is not None and current_depth >= depth:
            return []

        ids = [node["id"]]
        if "children" in node:
            for child in node["children"]:
                ids.extend(extract_ids_recursively(child, current_depth + 1))
        return ids

    if skip_canvas:
        return [
            id_
            for canvas in data["document"]["children"]
            for child in canvas['children']
            for id_ in extract_ids_recursively(child, 0)
        ]

    return [
        id_
        for child in data["document"]["children"]
        for id_ in extract_ids_recursively(child, 0)
    ]


def get_existing_images(images_dir):
    return set(os.listdir(images_dir))


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session



@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException, SSLError), max_tries=5,
    logger=logging.getLogger('backoff').addHandler(logging.StreamHandler())
)
def download_image(url, output_path, timeout=10):
    try:
        response = requests_retry_session().get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return url, output_path
    except Exception as e:
        tqdm.write(f"Error downloading {url}: {e}")
        return None, None


def fetch_and_save_images(url_and_path_pairs, num_threads=20):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_image, url, path): (url, path) for url, path in url_and_path_pairs}

        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Downloading images (Utilizing {num_threads} threads)", position=1, leave=False):
            url, downloaded_path = future.result()
            if downloaded_path:
                tqdm.write(f"Downloaded {url} to local directory {downloaded_path}")
            else:
                tqdm.write(f"Failed to download image: {url}")



def fetch_file_images(file_key, token):
    url = f"{API_BASE_URL}/files/{file_key}/images"
    headers = {"X-FIGMA-TOKEN": token}
    response = requests.get(url, headers=headers)
    data = response.json()

    if "error" in data and data["error"]:
        raise ValueError("Error fetching image fills")

    return data["meta"]["images"]


def fetch_node_images(file_key, ids, scale, format, token):
    max_retry = 3
    delay_between_429 = 10
    ids_chunk_size = 50
    ids_chunks = [
        ids[i: i + ids_chunk_size] for i in range(0, len(ids), ids_chunk_size)
    ]

    url = f"{API_BASE_URL}/images/{file_key}"
    headers = {"X-FIGMA-TOKEN": token}
    params = {
        "ids": "",
        "use_absolute_bounds": "true",
        "scale": scale,
        "format": format,
    }

    def fetch_images_chunk(chunk, retry=0):
        params["ids"] = ",".join(chunk)
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 429:
            if retry >= max_retry:
                raise ValueError(
                    f"Error fetching {len(chunk)} layer images. Rate limit exceeded."
                )

            # check if retry-after header is present
            retry_after = response.headers.get("retry-after")
            retry_after = int(
                retry_after) if retry_after else delay_between_429

            tqdm.write(
                f"HTTP429 - Waiting {retry_after} seconds before retrying...  ({retry + 1}/{max_retry})")
            time.sleep(retry_after)
            return fetch_images_chunk(chunk, retry=retry + 1)

        data = response.json()
        if "err" in data and data["err"]:
            raise ValueError(
                f"Error fetching {len(chunk)} layer images", data["err"]
            )
        return data["images"]

    max_concurrent_requests = 10
    delay_between_batches = 5
    num_batches = -(-len(ids_chunks) // max_concurrent_requests)

    tqdm.write(
        f"Fetching {len(ids)} layer images in {len(ids_chunks)} chunks, with {num_batches} batches...")

    image_urls = {}
    for batch_idx in tqdm(range(num_batches), desc="Batches", position=5, leave=False):
        start_idx = batch_idx * max_concurrent_requests
        end_idx = start_idx + max_concurrent_requests
        batch_chunks = ids_chunks[start_idx:end_idx]

        with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
            results = [result for result in tqdm(executor.map(
                fetch_images_chunk, batch_chunks), desc=f"Batch {batch_idx}", position=4, leave=False)]
            for chunk_result in results:
                image_urls.update(chunk_result)

        if batch_idx < num_batches - 1:
            tqdm.write(
                f"Entry {batch_idx + 1 + 1}/{num_batches}: Waiting {delay_between_batches} seconds before next batch...")
            time.sleep(delay_between_batches)

    return image_urls


@click.command()
@click.option("-dir", default="./downloads", type=click.Path(exists=True), help="Image format to bake the layers")
@click.option("-fmt", '--format',  default="png", help="Image format to bake the layers")
@click.option("-s", '--scale', default="1", help="Image scale")
@click.option("-d", '--depth',  default=None, help="Layer depth to go recursively", type=click.INT)
@click.option('--skip-canvas',  default=True, help="Skips the canvas while exporting images")
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-src", '--source-dir', default="./downloads/*.json", help="Path to the JSON file")
def main(dir, format, scale, depth, skip_canvas, figma_token, source_dir):
    root_dir = Path(dir)

    _src_dir = Path('/'.join(source_dir.split("/")[0:-1]))   # e.g. ./downloads
    _src_file_pattern = source_dir.split("/")[-1]            # e.g. *.json
    json_files = glob.glob(_src_file_pattern, root_dir=_src_dir)
    file_keys = [Path(file).stem for file in json_files]

    for key, json_file in tqdm(zip(file_keys, json_files), desc="Directories", position=10, leave=True, total=len(file_keys)):

        subdir = root_dir / key
        subdir.mkdir(parents=True, exist_ok=True)

        json_file = _src_dir / Path(json_file)

        if json_file.is_file():
            tqdm.write(f"Processing directory {subdir}")

            try:
              with open(json_file, "r") as file:
                file_data = json.load(file)

              if depth is not None:
                  depth = int(depth)

              # fetch and save thumbnail (if not already downloaded)
              if not (subdir / "thumbnail.png").is_file():
                thumbnail_url = file_data["thumbnailUrl"]
                download_image(thumbnail_url, subdir / "thumbnail.png")

              node_ids = get_node_ids(
                  file_data, depth=depth, skip_canvas=skip_canvas)
              # ----------------------------------------------------------------------
              # image fills
              images_dir = subdir / "images"
              images_dir.mkdir(parents=True, exist_ok=True)
              existing_images = os.listdir(images_dir)

              # TODO: this is not safe. the image fills still can be not complete if we terminate during the download
              # Fetch and save image fills (B)
              if not any(not re.match(r"\d+:\d+", img) for img in existing_images):
                  tqdm.write("Fetching image fills...")
                  image_fills = fetch_file_images(key, token=figma_token)
                  url_and_path_pairs = [
                      (url, os.path.join(images_dir, f"{hash_}.{format}"))
                      for hash_, url in image_fills.items()
                  ]
                  fetch_and_save_images(url_and_path_pairs)
              else:
                  tqdm.write("Image fills already fetched")

              # ----------------------------------------------------------------------
              # bakes
              images_dir = subdir / "bakes"
              images_dir.mkdir(parents=True, exist_ok=True)
              existing_images = os.listdir(images_dir)

              # Fetch and save layer images (A)
              node_ids_to_fetch = [
                  node_id
                  for node_id in node_ids
                  if f"{node_id}.{format}" not in existing_images
                  and f"{node_id}@{scale}x.{format}" not in existing_images
              ]

              if node_ids_to_fetch:
                  tqdm.write(
                      f"Fetching {len(node_ids_to_fetch)} of {len(node_ids)} layer images...")
                  layer_images = fetch_node_images(
                      key, node_ids_to_fetch, scale, format, token=figma_token)
                  url_and_path_pairs = [
                      (
                          url,
                          os.path.join(
                              images_dir,
                              f"{node_id}{'@' + str(scale) + 'x' if scale != '1' else ''}.{format}",
                          ),
                      )
                      for node_id, url in layer_images.items()
                  ]
                  fetch_and_save_images(url_and_path_pairs)
              else:
                  tqdm.write("Layer images already fetched")

              tqdm.write("All images fetched and saved successfully")
            except json.decoder.JSONDecodeError as e:
              tqdm.write(f"Error loading {json_file} Skipping... (Malformed JSON file))")

        else:
            tqdm.write(
                f"Skipping directory {subdir}: JSON file not found at '{json_file}'")


if __name__ == "__main__":
    main()