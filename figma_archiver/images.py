import glob
import logging
from multiprocessing import cpu_count
import threading
import click
import time
import json
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urlencode
from urllib3 import Retry
import backoff
from ssl import SSLError
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import queue



load_dotenv()

API_BASE_URL = "https://api.figma.com/v1"


@click.command()
@click.option("-dir", default="./downloads", type=click.Path(exists=True), help="Image format to bake the layers")
@click.option("-fmt", '--format',  default="png", help="Image format to bake the layers")
@click.option("-s", '--scale', default="1", help="Image scale")
@click.option("-d", '--depth',  default=None, help="Layer depth to go recursively", type=click.INT)
@click.option('--skip-canvas',  default=True, help="Skips the canvas while exporting images")
@click.option('--no-fills',  default=False, help="Skips the download for Image fills")
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-src", '--source-dir', default="./downloads/*.json", help="Path to the JSON file")
@click.option("-c", "--concurrency", help="Number of concurrent processes.", default=cpu_count(), type=int)
def main(dir, format, scale, depth, skip_canvas, no_fills, figma_token, source_dir, concurrency):
    img_queue = queue.Queue()
    root_dir = Path(dir)

    _src_dir = Path('/'.join(source_dir.split("/")[0:-1]))   # e.g. ./downloads
    _src_file_pattern = source_dir.split("/")[-1]            # e.g. *.json
    json_files = glob.glob(_src_file_pattern, root_dir=_src_dir)
    file_keys = [Path(file).stem for file in json_files]
    img_queue.put((None, None))  # Add a sentinel value to indicate the end of the queue


    download_thread = threading.Thread(target=image_queue_handler, args=(img_queue,))
    download_thread.start()

    # run the main thread loop

    # TODO: utilize the concurrency parameter
    # chunks = chunk_list(zip(file_keys, json_files), concurrency)
    # threads = []
    # for _ in range(concurrency):
    #   t = threading.Thread(target=process_files, args=(files, img_queue,))
    #   t.start()
    #   threads.append(t)
    # for t in threads:
    #   t.join()

    for key, json_file in tqdm(zip(file_keys, json_files), desc="Directories", position=10, leave=True, total=len(file_keys)):

        subdir = root_dir / key
        subdir.mkdir(parents=True, exist_ok=True)

        json_file = _src_dir / Path(json_file)
        file_data = read_file_data(json_file)

        if file_data:
          tqdm.write(f"{subdir} processing...")
          if depth is not None:
              depth = int(depth)
          # fetch and save thumbnail (if not already downloaded)
          if not (subdir / "thumbnail.png").is_file():
            thumbnail_url = file_data["thumbnailUrl"]
            download_image(thumbnail_url, subdir / "thumbnail.png")
            tqdm.write(f"Saved thumbnail to {subdir / 'thumbnail.png'}")

          node_ids = get_node_ids(
              file_data, depth=depth, skip_canvas=skip_canvas)
          # ----------------------------------------------------------------------
          # image fills
          if not no_fills:
            images_dir = subdir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            existing_images = os.listdir(images_dir)

            # TODO: this is not safe. the image fills still can be not complete if we terminate during the download
            # Fetch and save image fills (B)
            if not any(not re.match(r"\d+:\d+", img) for img in existing_images):
                # tqdm.write("Fetching image fills...")
                image_fills = fetch_file_images(key, token=figma_token)
                url_and_path_pairs = [
                    (url, os.path.join(images_dir, f"{hash_}.{format}"))
                    for hash_, url in image_fills.items()
                ]
                fetch_and_save_images(url_and_path_pairs, position=7)
            else:
                tqdm.write(f"{images_dir} - Image fills already fetched")

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
              # tqdm.write(f"Fetching {len(node_ids_to_fetch)} of {len(node_ids)} layer images...")
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
              fetch_and_save_images(url_and_path_pairs, position=8)
          else:
              tqdm.write(f"{images_dir} - Layer images already fetched")

          tqdm.write(f"{subdir} complete.")
        else:
          tqdm.write(
                f"Skipping directory {subdir}: Valid JSON file not found at '{json_file}'")

    # finally wait for the download thread to finish
    download_thread.join()

def process_files(files, image_queue):
    ...


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

def image_queue_handler(img_queue: queue.Queue, batch=20, timeout=300):
    def download_image_with_progress_bar(url_path, progress):
        url, path = url_path
        download_image(url, path)
        progress.update(1)
        return
    
    progress = tqdm(total=img_queue.qsize(), desc="Archiving Images", position=9)

    while True:
        items_to_process = []
        while True:
            try:
                url, path = img_queue.get(timeout=timeout)
                if url is None:
                    break
                items_to_process.append((url, path))
                progress.total += 1
            except queue.Empty:
                break

        if not items_to_process:
            break

        with ThreadPoolExecutor(max_workers=batch) as executor:
            download_func = partial(download_image_with_progress_bar, progress=progress)
            executor.map(download_func, items_to_process)

    progress.close()
    


def fetch_and_save_images(url_and_path_pairs, position=0, num_threads=20):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_image, url, path): (url, path) for url, path in url_and_path_pairs}

        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Downloading images (Utilizing {num_threads} threads)", position=position, leave=False):
            url, downloaded_path = future.result()
            if downloaded_path:
                tqdm.write(f"☑ {url} → {downloaded_path}")
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
    url = f"{API_BASE_URL}/images/{file_key}"
    headers = {"X-FIGMA-TOKEN": token}
    params = {
        "ids": "",
        "use_absolute_bounds": "true",
        "scale": scale,
        "format": format,
    }

    # figma server allows up to 5000 characters in the url (between 4000 ~ 6000 characters)
    def chunk(ids, url=url, params=params, max_len=5000):
        """
        chunk the ids for the api call to avoid the url max length limit.
        most browsers have a limit of 2048 characters, but for this case, it is safe to increase it to 4000
        use the url and params info to calculate the length of the api call
        the chunked ids will be formatted as id1,id2,id3
        """

        def get_chunk_len(chunk):
            return len(url) + len(",".join(chunk)) + len(urlencode(params))

        chunk = []
        for id_ in ids:
            if get_chunk_len(chunk + [id_]) > max_len:
                yield chunk
                chunk = []
            chunk.append(id_)
        yield chunk


    max_retry = 3
    delay_between_429 = 10
    ids_chunks = list(chunk(ids))


    def fetch_images_chunk(chunk, retry=0):
        params["ids"] = ",".join(chunk)
        try:
            response = requests.get(url, headers=headers, params=params)
        except requests.exceptions.ConnectionError as e:
            log_error(f"Error fetching {len(chunk)} layer images [{','.join(chunk)}], e:{e}")
            return {}

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
            # ignore and report error
            msg = f"Error fetching {len(chunk)} layer images [{','.join(chunk)}], e:{data['err']}"
            log_error(msg)
            return {}
        return data["images"]

    max_concurrent_requests = 10
    delay_between_batches = 5
    num_batches = -(-len(ids_chunks) // max_concurrent_requests)

    image_urls = {}
    with tqdm(range(num_batches), desc=f"Fetching ({len(ids)}/{len(ids_chunks)}/{num_batches})", position=2, leave=False) as pbar:
        for batch_idx in pbar:
            start_idx = batch_idx * max_concurrent_requests
            end_idx = start_idx + max_concurrent_requests
            batch_chunks = ids_chunks[start_idx:end_idx]

            with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
                results = [result for result in executor.map(fetch_images_chunk, batch_chunks)]
                for chunk_result in results:
                    image_urls.update(chunk_result)

            if batch_idx < num_batches - 1:
                pbar.set_description(
                    f"Entry {batch_idx + 1 + 1}/{num_batches}: Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)

    return image_urls


# utils

def log_error(msg, print=True):
    if print:
        tqdm.write(msg)

    # check if err log file exists
    err_log_file = Path("err.log")
    if not err_log_file.exists():
        with open(err_log_file, "w") as f:
            f.write("")
            f.close()
    
    with open(err_log_file, "a") as f:
        f.write(msg + "\n")
        f.close()


def read_file_data(file: Path):
    if file.is_file():
        try:
          with open(file, "r") as file:
            file_data = json.load(file)
            return file_data
        except json.decoder.JSONDecodeError as e:
          tqdm.write(f"Error loading {file} Skipping... (Malformed JSON file)) - error: {e.msg} {e.args}")

          # read the json file and print the start and end of it for debugging
          try:
            with open(file, "r") as file:
                  txt = file.read()
                  _first_few = txt[0: 100]
                  _last_few = txt[-100:]
                  tqdm.write(f"First few characters: \n{_first_few}")
                  tqdm.write(f"Last few characters: \n{_last_few}")
          except TypeError as e: ...
          return None
    else:
        tqdm.write(f"File {file} not found")
        return None



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

def chunk_list(input_list, n):
    return [input_list[i:i + n] for i in range(0, len(input_list), n)]



# main
if __name__ == "__main__":
    main()
