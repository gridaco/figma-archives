import glob
import logging
from multiprocessing import cpu_count
import random
import threading
import click
import time
import json
import os
import re
import shutil
import tempfile
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
from typing import List, Tuple
import resource
from PIL import Image
from datetime import datetime
import math
import io


resource.setrlimit(
    resource.RLIMIT_CORE,
    (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


load_dotenv()

API_BASE_URL = "https://api.figma.com/v1"
BOTTOM_POSITION = 24


@click.command()
@click.option("-v", "--version", default=0, type=click.INT, help="Version number to specify cache - update for new versions")
@click.option("-dir", default="./downloads", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="Directory for the images to be saved - ~dir/:key/images/.png")
@click.option("-fmt", '--format',  default="png", help="Image format to export the layers")
@click.option("-s", '--scale', default="1", help="Image scale")
@click.option("-d", '--depth',  default=None, help="Layer depth to go recursively", type=click.INT)
@click.option('--include-canvas',  default=False, help="Includes the canvas while exporting images (False by default)")
@click.option('--no-fills',  default=False, help="Skips the download for Image fills")
@click.option("--optimize", is_flag=True, help="Optimize images size (Now only applied to hash images)", default=False, type=click.BOOL)
@click.option("--max-mb-hash", help="Max mb to be applied to has images (if optimize is true)", default=1, type=click.INT)
@click.option('--only-thumbnails', is_flag=True, default=False, help="process only thumbnails. this is usefull when thumbnail is expired & files are fresh-fetched")
@click.option('--thumbnails', is_flag=True, default=False, help="Set this flag to download thumbnail.png as well")
@click.option('--only-sync', is_flag=True, default=False, help="Set this flag to only sync the files without downloading or optimizing images")
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-src", '--source-dir', default="./downloads/*.json", help="Path to the JSON file")
@click.option("-c", "--concurrency", help="Number of concurrent processes.", default=cpu_count(), type=int)
@click.option("--skip-n", help="Number of files to skip (for dubugging).", default=0, type=int)
@click.option("--no-download", is_flag=True, help="No downloading the images (This can be used if you want this script to only run for optimizing existing images)", default=0, type=int)
@click.option("--shuffle", is_flag=True, help="Rather if to randomize the input for even distribution", default=False, type=click.BOOL)
def main(version, dir, format, scale, depth, include_canvas, no_fills, optimize, max_mb_hash, thumbnails, only_thumbnails, only_sync, figma_token, source_dir, concurrency, skip_n, no_download, shuffle):
    # progress bar position config
    global BOTTOM_POSITION
    BOTTOM_POSITION = concurrency * 2 + 5

    if only_thumbnails:
        if thumbnails:
            tqdm.write(
                'Thumbnails only option passed. Ignoring other fills or export related options.')
            no_fills = True  # skip image fills
            depth = 0  # skip exports
        else:
            # error out
            click.echo(
                "Error: --only-thumbnails option requires --thumbnails option to be set as well")
            return

    # figma token
    if figma_token.startswith("[") and figma_token.endswith("]"):
        figma_tokens = json.loads(figma_token)
    else:
        figma_tokens = [figma_token]

    if not optimize:
        max_mb_hash = 0

    root_dir = Path(dir)

    _src_dir = Path('/'.join(source_dir.split("/")[0:-1]))   # e.g. ./downloads
    _src_file_pattern = source_dir.split("/")[-1]            # e.g. *.json
    json_files = glob.glob(_src_file_pattern, root_dir=_src_dir)
    json_files = json_files[skip_n:]
    file_keys = [Path(file).stem for file in json_files]

    # randomize for even distribution
    if shuffle:
        shuffled = [item for item in range(len(json_files))]
        random.shuffle(shuffled)
        json_files = [json_files[i] for i in shuffled]
        file_keys = [file_keys[i] for i in shuffled]

    # set up the queue and background downloader thread
    img_queue = queue.Queue()
    # download thread
    download_thread = threading.Thread(
        target=image_queue_handler, args=(img_queue,))
    download_thread.start()

    if not only_sync:
        # main progress bar
        pbar = tqdm(total=len(json_files),
                    position=BOTTOM_POSITION, leave=True)

        chunks = chunked_zips(file_keys, json_files, n=concurrency)
        threads: list[threading.Thread] = []

        tqdm.write(f"🔥 {concurrency} threads / {len(figma_tokens)} identities")

        # run the main thread loop
        # a accurate enough estimate for the progress bar. this is required since we cannot consume the zip iterator. - which means cannot get the size of the files inside each thread. this can be improved, but we're keeping it this way.
        size_avg = len(json_files) // concurrency
        for _ in range(concurrency):
            t = threading.Thread(target=process_files, args=(chunks[_],), kwargs={
                'root_dir': root_dir,
                'src_dir': _src_dir,
                'img_queue': img_queue,
                'include_canvas': include_canvas,
                'no_fills': no_fills,
                'thumbnails': thumbnails,
                'figma_token': figma_tokens[(_ + 1) % len(figma_tokens)],
                'format': format,
                'scale': scale,
                'optimize': optimize,
                'max_mb_hash': max_mb_hash,
                'depth': depth,
                'size': size_avg,
                'index': _,
                'pbar': pbar,
                'no_download': no_download,
                'concurrency': concurrency
            })
            t.start()
            threads.append(t)
            # # give each thread a little time difference to prevent 429
            # time.sleep(10)

        for t in threads:
            t.join()

        tqdm.write("All done!")
    # Signal the handler to stop by adding a None item
    img_queue.put(('EOD', 'EOD', None))
    # finally wait for the download thread to finish
    download_thread.join()

    # validation & meta sync
    for _ in tqdm(json_files, desc="🔥 Final Validation & Meta Sync", position=BOTTOM_POSITION, leave=True):
        key = Path(_).stem
        sync_metadata_for_exports(root_dir=root_dir, src_dir=_src_dir, key=key)
        sync_metadata_for_hash_images(
            root_dir=root_dir, src_dir=_src_dir, key=key)
        tqdm.write(f"🔥 {root_dir/key}")


def process_files(files, root_dir: Path, src_dir: Path, img_queue: queue.Queue, include_canvas: bool, no_fills: bool, thumbnails: bool, figma_token: str, format: str, scale: int, optimize: bool, max_mb_hash: int, depth: int, index: int, size: int, pbar: tqdm, concurrency: int, no_download: bool):
    # for key, json_file in files:
    for key, json_file in tqdm(files, desc=f"⚡️ {figma_token[:8]}", position=BOTTOM_POSITION-(index+4), leave=True, total=size):
        subdir: Path = root_dir / key
        subdir.mkdir(parents=True, exist_ok=True)

        json_file = src_dir / Path(json_file)
        file_data = read_file_data(json_file)

        if file_data:
            if depth is not None:
                depth = int(depth)
            if thumbnails:
                # fetch and save thumbnail (if not already downloaded)
                if not (subdir / "thumbnail.png").is_file() and not no_download:
                    thumbnail_url = file_data["thumbnailUrl"]
                    download_image(thumbnail_url, subdir / "thumbnail.png")
                    # tqdm.write(f"Saved thumbnail to {subdir / 'thumbnail.png'}")

            node_ids, depths, maxdepth = get_node_ids_and_depths(
                file_data, depth=depth, include_canvas=include_canvas)
            # ----------------------------------------------------------------------
            # image fills
            if not no_fills:
                images_dir = subdir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                existing_images = os.listdir(images_dir)

                # TODO: this is not safe. the image fills still can be not complete if we terminate during the download
                # Fetch and save image fills (B)
                if len(existing_images) == 0 and not no_download:
                    # tqdm.write("Fetching image fills...")
                    image_fills = fetch_file_images(key, token=figma_token)
                    url_and_path_pairs = [
                        (url, os.path.join(images_dir, f"{hash_}.{format}"))
                        for hash_, url in image_fills.items()
                    ]

                    # we don't use queue for has images
                    fetch_and_save_image_fills(
                        url_and_path_pairs, max_mb=max_mb_hash)
                    # for pair in url_and_path_pairs:
                    #   img_queue.put(pair + (max_mb_hash,))
                else:
                    # tqdm.write(f"{images_dir} - Image fills already fetched")
                    ...
                    if optimize:
                        for image in existing_images:
                            file = images_dir / image
                            success, saved = optimize_image(
                                file, max_mb=max_mb_hash)
                            if success:
                                tqdm.write(
                                    f"☑ {fixstr(f'(existing) Saved {(saved / 1024 / 1024):.2f}MB')}... → {file}")

            # ----------------------------------------------------------------------
            # exports
            images_dir = subdir / "exports"
            images_dir.mkdir(parents=True, exist_ok=True)
            existing_images = os.listdir(images_dir)

            # Fetch and save layer images (A)
            node_ids_to_fetch = [
                node_id
                for node_id in node_ids
                if f"{node_id}.{format}" not in existing_images
                and f"{node_id}@{scale}x.{format}" not in existing_images
            ]

            if node_ids_to_fetch and not no_download:
                # tqdm.write(f"Fetching {len(node_ids_to_fetch)} of {len(node_ids)} layer images...")
                layer_images = fetch_node_images(
                    key, node_ids_to_fetch, scale, format, token=figma_token, position=BOTTOM_POSITION-((concurrency*2)+index), conncurrency=concurrency)
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
                for pair in url_and_path_pairs:
                    img_queue.put(pair + (None,))
            else:
                # tqdm.write(f"{images_dir} - Layer images already fetched")
                ...

            tqdm.write(f"☑ {subdir}")
        else:
            tqdm.write(f"☒ {subdir}")
        pbar.update(1)


def requests_retry_session(
    retries=3,
    backoff_factor=1,
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
    backoff.expo, (requests.exceptions.RequestException,
                   SSLError), max_tries=5,
    logger=logging.getLogger('backoff').addHandler(logging.StreamHandler())
)
def download_image(url, output_path, max_mb=None, timeout=10):
    if url is None:
        return None, None
    try:
        response = requests_retry_session().get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
            f.close()

        if max_mb is not None and max_mb > 0:
            success, saved = optimize_image(output_path, max_mb=max_mb)
            if (success):
                tqdm.write(
                    f"☑ {fixstr(f'Optimized - saved {(saved / 1024 / 1024):.2f}MB')}... → {output_path}")
        return url, output_path
    # check if 403 Forbidden
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            log_error(f"☒ {fixstr(f'Forbidden (Expired): {url}')}", print=True)
            return None, None
        else:
            tqdm.write(f"☒ Error downloading {url}: {e}")
            return None, None
    except Exception as e:
        tqdm.write(f"☒ Error downloading {url}: {e}")
        return None, None


def download_image_with_progress_bar(item, progress):
    url, path, max_mb = item
    download_image(url, path, max_mb=max_mb)
    progress.update(1)


def image_queue_handler(img_queue: queue.Queue, batch=64):
    emojis = ['📭', '📬', '📫']

    total = 0
    while True:
        items_to_process = []
        url = None

        progress = tqdm(
            total=batch, desc=f"📭 ({total}/{total+img_queue.qsize()})", position=BOTTOM_POSITION-2, leave=False)

        while len(items_to_process) < batch:
            try:
                url, path, max_mb = img_queue.get(timeout=1)
                if url == 'EOD':  # Check for sentinel value ('EOD', 'EOD')
                    break

                if url is not None:
                    items_to_process.append((url, path, max_mb))
                    total += 1
                    progress.desc = f"📭 ({total}/{len(items_to_process)}/{batch}/{total}/{total+img_queue.qsize()})"
            except queue.Empty:
                ...

        if url == 'EOD':  # Break the outer loop if sentinel value is encountered
            tqdm.write("⏰ sentinel value encountered")
            break

        if not items_to_process:
            break

        progress.desc = f"{random.choice(emojis)}"
        with ThreadPoolExecutor(max_workers=batch) as executor:
            download_func = partial(
                download_image_with_progress_bar, progress=progress)
            executor.map(download_func, items_to_process)

        time.sleep(0.1)
        progress.close()

    tqdm.write("✅ Image Archiving Complete")


def fetch_and_save_image_fills(url_and_path_pairs, max_mb=1, position=5, num_threads=64):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download_image, url, path, max_mb): (
            url, path) for url, path in url_and_path_pairs}

        if position is not None:
            futures = tqdm(as_completed(futures), total=len(
                futures), desc=f"Downloading images (Utilizing {num_threads} threads)", position=position, leave=False)
        else:
            futures = as_completed(futures)

        for future in futures:
            url, downloaded_path = future.result()
            if downloaded_path:
                tqdm.write(f"☑ {fixstr(url)} → {downloaded_path}")
                if max_mb is not None and max_mb > 0:
                    optimize_image(downloaded_path, max_mb=max_mb)
            else:
                tqdm.write(f"Failed to download image: {url}")


def fixstr(str, n=64):
    """
    if str is longer than n, return first n characters
    if str is shorter than n, return str with spaces added to end
    """
    if len(str) > n:
        return str[:n]
    else:
        return str + " " * (n - len(str))


mb = 1024 * 1024


def optimize_image(path, max_mb=1):
    margin = 0.3
    try:
        startsize = os.path.getsize(path)
        max_size = max_mb * mb
        # Check if the image is already smaller than the target size
        if startsize <= max_size:
            return None, None
        target_bytes = max_size - (margin * mb)
        # Open the image
        img = Image.open(path)
        # Calculate the current number of bytes
        current_bytes = io.BytesIO()
        img.save(current_bytes, format='PNG')
        current_bytes = current_bytes.tell()
        if current_bytes > max_size:
            # Calculate the scale factor
            scale_factor = math.sqrt(target_bytes / current_bytes)
            # Calculate the new size
            new_size = tuple(int(dim * scale_factor) for dim in img.size)
            # Resize the image
            img = img.resize(new_size, resample=Image.BICUBIC)
        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as tmp:
            img.save(tmp.name, format='PNG')
            # Remove the original file before copying the temporary file

            # double check if it actually got smaller
            if os.path.getsize(tmp.name) > startsize:
                return False, 0

            # Remove the original file before moving the temporary file to the original filename
            os.remove(path)
            shutil.move(tmp.name, path)
        endsize = os.path.getsize(path)
        saved = startsize - endsize
        return True, saved
    except Exception as e:
        tqdm.write(f"☒ Error optimizing {path}: {e}")
        return False, 0


def fetch_file_images(file_key, token):
    url = f"{API_BASE_URL}/files/{file_key}/images"
    headers = {"X-FIGMA-TOKEN": token}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
    except requests.exceptions.ConnectionError as e:
        return {}

    if "error" in data and data["error"]:
        raise ValueError("Error fetching image fills")
    try:
        return data["meta"]["images"]
    except KeyError:
        return {}


def fetch_node_images(file_key, ids, scale, format, token, position, conncurrency):
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

    max_retry = 5 * conncurrency
    delay_between_429 = 5
    ids_chunks = list(chunk(ids))

    def fetch_images_chunk(chunk, retry=0):
        params["ids"] = ",".join(chunk)
        try:
            response = requests.get(url, headers=headers, params=params)
        except requests.exceptions.ConnectionError as e:
            return {}
        except requests.exceptions.JSONDecodeError as e:
            return {}
        except json.decoder.JSONDecodeError as e:
            return {}

        if response.status_code == 429:
            if retry >= max_retry:
                log_error(
                    f"Error fetching [{(','.join(chunk))}] layer images. Rate limit exceeded.")
                tqdm.write(
                    f"☒ HTTP429 - Rate limit exceeded. ({max_retry} tries)")
                return {}

            # check if retry-after header is present
            retry_after = response.headers.get("retry-after")
            retry_after = int(
                retry_after) if retry_after else delay_between_429 * (retry + 1) * conncurrency

            if max_retry - retry < 2:
                # only show the last retry message
                tqdm.write(
                    f"☒ HTTP429 - Waiting {retry_after} seconds before retrying...  ({retry + 1}/{max_retry})")
            time.sleep(retry_after)
            return fetch_images_chunk(chunk, retry=retry + 1)

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            return {}

        if "err" in data and data["err"]:
            # ignore and report error
            msg = f"Error fetching {len(chunk)} layer images [{','.join(chunk)}], e:{data['err']}"
            log_error(msg)
            return {}
        return data["images"]

    max_concurrent_requests = conncurrency
    num_batches = -(-len(ids_chunks) // max_concurrent_requests)
    batch_chunks = chunked_list(ids_chunks, num_batches)

    # TODO: group the batches to one ThreadPoolExecutor
    # TODO: the below logic seems duplicated.
    emojis = ['🛫', '🛬']
    image_urls = {}
    with tqdm(range(num_batches), desc=f"{random.choice(emojis)} ({len(ids)}/{len(ids_chunks)}/{num_batches})", position=position, leave=False, mininterval=1) as pbar:
        for batch_idx in pbar:
            for _chunk in batch_chunks[batch_idx]:
                pbar.set_description(
                    f"{random.choice(emojis)} {batch_idx + 1 + 1}/{num_batches}: Fetching...")
                image_urls.update(fetch_images_chunk(chunk=_chunk))

            if batch_idx < num_batches - 1:
                delay_between_batches = 3
                pbar.set_description(
                    f"{random.choice(emojis)} {batch_idx + 1 + 1}/{num_batches}: Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)

    return image_urls


def calculate_program():
    """
    calculates the stats of the program before starting the loop. this is helpful to show the progress bar.
    """
    ...


# utils

def log_error(msg, print=False):
    try:
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
    except Exception as e:
        ...


def save_optimization_info(root_dir, key, image, optimization):
    """
    TODO:
    """
    path = Path(root_dir) / key / "images"
    metadata = path / "meta.json"  # would be /:filekey/exports/meta.json
    is_new = not metadata.exists()
    # read the metadata
    with open(metadata, "w+") as f:
        try:
            olddata = json.load(f) if not is_new else {}
        except json.JSONDecodeError:
            olddata = {}

        data = {
            **olddata,
            "optimization": {
                **(olddata["optimization"] if "optimization" in olddata else {}),
                # saves the scale factor (if optimized)
                [image]: {
                    "scale": optimization["scale"],
                    "original": {
                        "size": optimization["original_size"],
                        "width": optimization["original_width"],
                        "height": optimization["original_height"],
                    },
                    "loss": optimization["loss"]
                }
            }
        }
        json.dump(data, f, separators=(',', ':'))
        f.close()


def sync_metadata_for_hash_images(root_dir, src_dir, key):
    """
    syncs the meta.json file for the hash images
    """
    path = Path(root_dir) / key / "images"
    document = read_file_data(Path(src_dir) / f"{key}.json")
    metadata: Path = path / "meta.json"  # would be /:filekey/exports/meta.json
    files = [Path(file) for file in filter_graphic_files(os.listdir(path))]
    hashes = [file.stem for file in files]

    is_new = not metadata.exists()
    # save the info file
    with open(metadata, "w+") as f:
        try:
            olddata = json.load(f) if not is_new else {}
        except json.JSONDecodeError:
            olddata = {}

        images = {}
        for hash_ in hashes:
            # hash : file
            file = [file for file in files if file.stem == hash_][0]
            images[hash_] = file.name

        data = {
            **olddata,
            # follows the figma-api format, "meta" key shall not be changed
            "document": {
                "version": document["version"],
                "lastModified": document["lastModified"]
            },
            # the last mod date of the meta file (a.k.a last archived)
            "archivedAt": datetime.now().isoformat(),
            "meta": {
                "images": images
            },
        }

        json.dump(data, f, separators=(',', ':'))
        f.close()


def sync_metadata_for_exports(root_dir, src_dir, key):
    """
    Saves the metadata under the root directory (of the file) to indicate which images are fulfilled.
    """

    path = Path(root_dir) / key / "exports"
    document = read_file_data(Path(src_dir) / f"{key}.json")
    metadata = path / "meta.json"  # would be /:filekey/exports/meta.json

    ids, depths, maxdepth = get_node_ids_and_depths(
        document, depth=None, include_canvas=True)  # get all ids

    # filter out only graphic files
    exports = filter_graphic_files(os.listdir(path))

    node_exports = {}
    for id_ in ids:
        # init the map
        node_exports[id_] = []

    # if the file has no @nx suffix, it's the @1x file
    for export in exports:
        name, scale, fmt = scale_and_format_from_name(export)
        node_exports[name].append(f"@{scale}x.{fmt}")

    # validate the resolutions
    # "resolutions": [
    #     # depth, scale, format
    #     [0, 1, "png"],
    #     [0, 2, "png"],
    #     [1, 1, "png"],
    #     [1, 2, "png"],
    # ]
    resolutions = []
    for depth in range(maxdepth):
        ids = [key for key, v in depths.items() if v == depth]
        exports = [export for id_ in ids for export in node_exports[id_]]
        scales_and_formats = [scale_and_format_from_name(
            export) for export in exports]
        scales = set([s for _, s, _ in scales_and_formats])
        formats = set([f for _, _, f in scales_and_formats])

        for scale in scales:
            for fmt in formats:
                if all((f"@{scale}x.{fmt}" in node_export or f".{fmt}" in node_export) for node_export in exports):
                    resolutions.append([depth, scale, fmt])

    # reversed_depths
    depths_ids_map = {}
    for k, v in depths.items():
        # the depth to be saved follows the format from figma api, where it starts from 1, not 0, where 1 is page (canvas), 2 being top level nodes.
        depths_ids_map.setdefault(v + 1, []).append(k)

    data = {
        "document": {
            "version": document["version"],
            "lastModified": document["lastModified"]
        },
        # the last mod date of the meta file (a.k.a last archived)
        "archivedAt": datetime.now().isoformat(),
        "resolutions": resolutions,  # the resolutions that are exported
        "map": node_exports,
        "depths": {
            "min": 1,
            "max": maxdepth + 1,
            **depths_ids_map
        },
    }

    # save the info file
    with open(metadata, "w") as f:
        json.dump(data, f, separators=(',', ':'))
        f.close()


def read_file_data(file: Path):
    if file.is_file():
        try:
            with open(file, "r") as file:
                file_data = json.load(file)
                return file_data
        except json.decoder.JSONDecodeError as e:
            log_error(
                f"Error loading {file} Skipping... (Malformed JSON file)) - error: {e.msg} {e.args}")

            # read the json file and print the start and end of it for debugging
            try:
                with open(file, "r") as file:
                    txt = file.read()
                    _first_few = txt[0: 100]
                    _last_few = txt[-100:]
                    tqdm.write(f"First few characters: \n{_first_few}")
                    tqdm.write(f"Last few characters: \n{_last_few}")
            except TypeError as e:
                ...
            return None
    else:
        tqdm.write(f"File {file} not found")
        return None


def get_node_ids_and_depths(data, depth=None, include_canvas=False):
    """
    Returns a tuple of two lists:
    1. The IDs of the nodes.
    2. A dictionary that maps each ID to its depth in the tree.
    """
    def extract_ids_recursively(node, current_depth):
        if depth is not None and current_depth > depth:
            return [], {}

        ids = [node["id"]]
        depth_map = {node["id"]: current_depth}

        if "children" in node:
            for child in node["children"]:
                child_ids, child_depth_map = extract_ids_recursively(
                    child, current_depth + 1)
                ids.extend(child_ids)
                depth_map.update(child_depth_map)
        return ids, depth_map

    if include_canvas:
        ids, depth_map = zip(*[
            extract_ids_recursively(child, 0)
            for child in data["document"]["children"]
        ])
    else:
        ids, depth_map = zip(*[
            extract_ids_recursively(child, 0)
            for canvas in data["document"]["children"]
            for child in canvas['children']
        ])

    # Flatten lists and merge dictionaries
    ids = [id_ for sublist in ids for id_ in sublist]
    depth_map = {k: v for dict_ in depth_map for k, v in dict_.items()}
    max_depth = max(depth_map.values())

    return ids, depth_map, max_depth


def get_existing_images(images_dir):
    return set(os.listdir(images_dir))


def chunked_zips(a: list, b: list, n: int) -> List[zip]:
    zipsize = len(a)
    per_zip = zipsize // n
    remainder = zipsize - per_zip * n
    zips = []
    for i in range(n - 1):
        start = i * per_zip
        end = start + per_zip
        _a = a[start:end]
        _b = b[start:end]
        zips.append(zip(_a, _b))
    start = (n - 1) * per_zip
    end = start + per_zip + remainder
    _a = a[start:end]
    _b = b[start:end]
    zips.append(zip(_a, _b))
    return zips


def chunked_list(a: list, n: int) -> List[zip]:
    listsize = len(a)
    perlist = listsize // n
    remainder = listsize - perlist * n
    chunks = []
    for i in range(n - 1):
        start = i * perlist
        end = start + perlist
        _a = a[start:end]
        chunks.append(_a)
    start = (n - 1) * perlist
    end = start + perlist + remainder
    _a = a[start:end]
    chunks.append(_a)
    return chunks


GRAPHIC_FORMATS = [
    ".png",
    ".jpg",
    ".svg",
    ".pdf",
]


def filter_graphic_files(files):
    return [
        file
        for file in files
        if any(
            file.endswith(fmt)
            for fmt in GRAPHIC_FORMATS
        )
    ]


def scale_and_format_from_name(name):
    """
    returns the scale and format from the name of the file.
    """
    name, fmt = name.split(".")
    fmt = fmt.lower()

    if "@" in name:
        name, scale = name.split("@")
        scale = float(scale.replace("x", ""))
        # if scale is n.0 return (int) n
        if scale.is_integer():
            scale = int(scale)
    else:
        scale = 1

    return name, scale, fmt


# main
if __name__ == "__main__":
    main()
