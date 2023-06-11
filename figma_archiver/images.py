import glob
import logging
import mimetypes
from multiprocessing import cpu_count
import random
import threading
import click
import time
import json
import os
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
from typing import List, Callable
import resource
from PIL import Image, ImageFile, UnidentifiedImageError
from PIL.PngImagePlugin import PngInfo
from datetime import datetime
import math
import logging
from colorama import Fore
import numpy as np
import resource


# TODO: gifRef support


ImageFile.LOAD_TRUNCATED_IMAGES = True


# configure logging
logging.basicConfig(
    filename="figma_archiver.log",
    filemode="a",
    level=logging.WARN,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


resource.setrlimit(
    resource.RLIMIT_CORE,
    (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


load_dotenv()

API_BASE_URL = "https://api.figma.com/v1"


@click.command()
@click.option("-v", "--version", default=0, type=click.INT, help="Version number to specify cache - update for new versions")
@click.option("-dir", default="./downloads", type=click.Path(file_okay=False, dir_okay=True), help="Directory for the images to be saved - ~dir/:key/images/.png")
@click.option("-fmt", '--format',  default="png", help="Image format to export the layers")
@click.option("-s", '--scale', default="1", help="Image scale")
@click.option("-d", '--depth',  default=None, help="Layer depth to go recursively", type=click.INT)
@click.option('--include-canvas',  default=False, help="Includes the canvas while exporting images (False by default)")
@click.option('--no-fills', is_flag=True, default=False, help="Skips the download for Image fills")
@click.option("--optimize", is_flag=True, help="Optimize images size (Now only applied to hash images)", default=False, type=click.BOOL)
@click.option("--no-exports", is_flag=True, default=False, help="Skips the download for Node exports")
@click.option("--max-mb-hash", help="Max mb to be applied to has images (if optimize is true)", default=None, type=click.INT)
@click.option('--only-thumbnails', is_flag=True, default=False, help="process only thumbnails. this is usefull when thumbnail is expired & files are fresh-fetched")
@click.option('--types', default=None, help="specify the type of node to be fetched", type=click.STRING)
@click.option('--thumbnails', is_flag=True, default=False, help="Set this flag to download thumbnail.png as well")
@click.option('--only-sync', is_flag=True, default=False, help="Set this flag to only sync the files without downloading or optimizing images")
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("-src", '--source-dir', default="./downloads/*.json", help="Path to the JSON file")
@click.option("-c", "--concurrency", help="Number of concurrent processes.", default=cpu_count(), type=int)
@click.option("--skip-n", help="Number of files to skip (for dubugging).", default=0, type=int)
@click.option("--no-download", is_flag=True, help="No downloading the images (This can be used if you want this script to only run for optimizing existing images)", default=0, type=int)
@click.option("--shuffle", is_flag=True, help="Rather if to randomize the input for even distribution", default=False, type=click.BOOL)
@click.option("--sample", default=None, help="Sample n files from the input", type=click.INT)
@click.option("--hide-progress", help="Hide progress bar", default=None, type=click.Choice([True, False, None, "*", "c"]))
def main(version, dir, format, scale, depth, include_canvas, no_fills, optimize, no_exports, max_mb_hash, types, thumbnails, only_thumbnails, only_sync, figma_token, source_dir, concurrency, skip_n, no_download, shuffle, sample, hide_progress):

    # progress display config
    hide_progress_main = False
    hide_progress_c = False
    if hide_progress is not None:
        if hide_progress == "*":
            hide_progress_main = True
            hide_progress_c = True
        elif hide_progress == "c":
            hide_progress_c = True
        else:
            hide_progress_main = True
            hide_progress_c = True

    # Get current limit
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

    click.echo(f'Soft limit starts as: {soft_limit}')
    # Try to update the limit
    resource.setrlimit(resource.RLIMIT_NOFILE,
                       ((concurrency + 1) * 64 * 2, hard_limit))

    # Verify it now
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

    click.echo(f'Soft limit changed to: {soft_limit}')

    # progress bar position config
    global BOTTOM_POSITION

    cbars = 0 if hide_progress_c else 1
    if not hide_progress_c:
        if not no_fills:
            cbars += 1
        if not no_exports:
            cbars += 1

    BOTTOM_POSITION = ((concurrency + 2) * cbars) + 4

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

    if no_exports:
        depth = 0

    if types is not None:
        # split and trim
        types = [
            type.strip() for type in
            types.split(",")
        ]

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
    json_files = json_files[:sample] if sample else json_files
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
                    position=pbarpos(0), leave=True, disable=hide_progress_main)

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
                'no_exports': no_exports,
                'thumbnails': thumbnails,
                'types': types,
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
                'concurrency': concurrency,
                'hide_progress': hide_progress_c
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
    for _ in tqdm(json_files, desc="🔥 Final Validation & Meta Sync", position=pbarpos(0), leave=True):
        key = Path(_).stem
        sync_metadata_for_exports(root_dir=root_dir, src_dir=_src_dir, key=key)
        sync_metadata_for_hash_images(
            root_dir=root_dir, src_dir=_src_dir, key=key)
        tqdm.write(f"🔥 {root_dir/key}")


def process_files(files, root_dir: Path, src_dir: Path, img_queue: queue.Queue, include_canvas: bool, no_fills: bool, no_exports: bool, thumbnails: bool, types: list[str], figma_token: str, format: str, scale: int, optimize: bool, max_mb_hash: int, depth: int, index: int, size: int, pbar: tqdm, concurrency: int, no_download: bool, hide_progress: bool):
    # for key, json_file in files:
    for key, json_file in tqdm(files, desc=fixstr(f"⚡️ C{index + 1}", 6), position=pbarpos(0, index=index, margin=4, batch=concurrency), leave=True, total=size, disable=hide_progress):
        subdir: Path = root_dir / key
        subdir.mkdir(parents=True, exist_ok=True)

        json_file = src_dir / Path(json_file)
        file_data = read_file_data(json_file)
        # indicates if process is satisfied - change to false if any of the conditions are not met
        # this only works for blocked process [thumbnail, fills] and does not work for [exports] - we can't check if the exports download is complete (it uses the image queue, while fills does not)
        satisfied = True
        skipped = True

        if file_data:
            if depth is not None:
                depth = int(depth)
            if thumbnails:
                # fetch and save thumbnail (if not already downloaded)
                if not (subdir / "thumbnail.png").is_file() and not no_download:
                    thumbnail_url = file_data["thumbnailUrl"]
                    download(thumbnail_url, subdir / "thumbnail.png")
                    skipped = False
                    # tqdm.write(f"Saved thumbnail to {subdir / 'thumbnail.png'}")

            node_ids, depths, maxdepth = get_node_ids_and_depths(
                file_data, depth=depth, include_canvas=include_canvas, types=types)
            # ----------------------------------------------------------------------
            # image fills
            if not no_fills:
                images_dir = subdir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                existing_images = get_existing_images(images_dir)

                paint_map = image_paint_map(file_data["document"])
                # Figma api also returns hashes for images that are not used in the file. We need to filter them out
                hashes = paint_map.keys()
                existing_hashes = [
                    Path(image).stem for image in existing_images]

                hashes_to_download = [
                    # filter out the hashes that are already downloaded
                    # => if hash is not in existing_hashes
                    hash for hash in hashes if hash not in existing_hashes
                ]

                def optimizer(path):
                    hash = Path(path).stem
                    # tqdm.write(hash, paint_map)
                    # print(hashes, hash, paint_map, json_file)
                    opt = optimized_image_paint_map(
                        paint_map={hash: paint_map[hash]},
                        images={
                            hash: path
                        }
                    )

                    max_width = opt[hash].get("max", {}).get("width", None)
                    max_height = opt[hash].get(
                        "max", {}).get("height", None)

                    success, saved, dimA, dimB, scale = optimize_image(
                        path=path,
                        max_size=(
                            max_mb_hash*mb) if max_mb_hash else None,
                        max_width=max_width, max_height=max_height
                    )
                    if success:
                        aw, ah = dimA
                        bw, bh = dimB
                        # tqdm.write(
                        #     Fore.BLUE +
                        #     f"☑ {fixstr(f'(optimized) {(saved / mb):.2f}MB @x{scale:.2f} {aw}x{ah} → {bw}x{bh} (max: {int(max_width) if max_width is not None else 0}x{int(max_height) if max_height is not None else 0} | {max_mb_hash}mb) {hash} ...')} → {path}"
                        #     + Fore.RESET
                        # )
                        #     tqdm.write(
                        #         f"☑ {fixstr(f'(existing) Saved {(saved / mb):.2f}MB')}... → {file}")

                # Fetch and save image fills (B)
                if len(hashes_to_download) > 0 and not no_download:
                    # tqdm.write("Fetching image fills...")
                    image_fills = fetch_file_images(key, token=figma_token)
                    url_and_path_pairs = [
                        (url, images_dir / hash_)
                        for hash_, url in image_fills.items()
                    ]

                    # update the url_and_path_pairs to only include the hases that is in hashes_to_download
                    # the path from above does not have extension, we don't need to use .stem but .name
                    url_and_path_pairs = [
                        (url, path) for url, path in url_and_path_pairs if path.name in hashes_to_download
                    ]

                    if len(url_and_path_pairs) > 0:
                        # we don't use queue for has images
                        fetch_and_save_image_fills(
                            file_key=key, url_and_path_pairs=url_and_path_pairs, optimizer=(
                                optimizer if optimize else None),
                            position=pbarpos(
                                3, index=index, margin=6, batch=concurrency),
                            hide_progress=hide_progress
                        )
                        skipped = False

                    # validate the images - list the images, compare if all is downloaded from (hashes)
                    existing_images = get_existing_images(images_dir)
                    existing_hashes = [
                        Path(image).stem for image in existing_images]
                    # check if all hashes are downloaded (check if two lists are equal, compare each item)
                    if len(hashes) != len(existing_hashes) or not all([hash in existing_hashes for hash in hashes]):
                        satisfied = False

                else:
                    # tqdm.write(f"{images_dir} - Image fills already fetched")
                    ...
                    if optimize:
                        for image in existing_images:
                            file = images_dir / image
                            optimizer(file)

            # ----------------------------------------------------------------------
            # exports
            if not no_exports:
                images_dir = subdir / "exports"
                images_dir.mkdir(parents=True, exist_ok=True)
                existing_images = get_existing_images(images_dir)

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
                        key, node_ids_to_fetch, scale, format,
                        token=figma_token,
                        position=pbarpos(
                            1, index=index, margin=5, batch=concurrency),
                        conncurrency=concurrency)
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
                    skipped = False
                else:
                    # tqdm.write(f"{images_dir} - Layer images already fetched")
                    ...
        if satisfied:
            color = Fore.YELLOW if skipped else Fore.GREEN
            tqdm.write(color + f"☑ {subdir}" + Fore.RESET)
        else:
            tqdm.write(Fore.RED + f"☒ {subdir}" + Fore.RESET)
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


def validate_image(image_path):
    """Check if the image is valid or not."""
    try:
        Image.open(image_path).verify()
        return True
    except (IOError, SyntaxError):
        return False


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,
                   SSLError), max_tries=5,
    logger=logging.getLogger('backoff').addHandler(logging.StreamHandler())
)
def download(url, output_path: str | Path, timeout=10):
    # path as string
    output_path = str(output_path)

    if url is None:
        return None, None
    try:
        response = requests_retry_session().get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        mimetype = mimetypes.guess_extension(response.headers["Content-Type"])
        if not '.' in output_path:
            output_path = f'{output_path}{mimetype}'
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        # if image,
        if mimetype in GRAPHIC_FORMATS:
            # check if the image is valid, if not delete it
            if not validate_image(output_path):
                os.remove(output_path)
                raise ValueError(
                    "The downloaded image is truncated or corrupted.")
        return url, output_path
    # check if 403 Forbidden
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            log_error(f"☒ {fixstr(f'Forbidden (Expired): {url}')}", print=True)
            return None, None
        else:
            tqdm.write(Fore.YELLOW +
                       f"☒ Error {e} while downloading {url}" + Fore.RESET)
            return None, None
    # check if TimeoutError (& ReadTimeout)
    except requests.exceptions.Timeout as e:
        log_error(f"☒ {fixstr(f'Timeout: {url}')}", print=True)
        return None, None

    except Exception as e:
        log_error(
            f"☒ {(f'Error {e} while downloading {url}')}", print=True)
        return None, None


def image_queue_handler(img_queue: queue.Queue, batch=64):
    def download_image_with_progress_bar(item, progress):
        url, path, pp = item
        # TODO: use post processing
        download(url, path)
        progress.update(1)

    emojis = ['📭', '📬', '📫']

    total = 0
    while True:
        items_to_process = []
        url = None

        progress = tqdm(
            total=batch, desc=f"📭 ({total}/{total+img_queue.qsize()})", position=pbarpos(0, margin=2), leave=False)

        while len(items_to_process) < batch:
            try:
                url, path, pp = img_queue.get(timeout=1)
                if url == 'EOD':  # Check for sentinel value ('EOD', 'EOD')
                    break

                if url is not None:
                    items_to_process.append((url, path, pp))
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


PostProcessor = Callable[[str], None]
Optimizer = PostProcessor


def fetch_and_save_image_fills(file_key, url_and_path_pairs, optimizer: Optimizer, position=4, num_threads=64, hide_progress=False):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(download, url, path): (
            url, path) for url, path in url_and_path_pairs}

        if position is not None:
            futures = tqdm(as_completed(futures), total=len(
                futures), desc=f"📷 {file_key[:5]} (C{num_threads})", position=position, leave=False, disable=hide_progress)
        else:
            futures = as_completed(futures)

        for future in futures:
            url, downloaded_path = future.result()
            if downloaded_path:
                # tqdm.write(
                #     Fore.WHITE + f"☑ {fixstr(url)} → {downloaded_path}" + Fore.RESET)
                if optimizer is not None:
                    optimizer(downloaded_path)
            else:
                log_error(f"☒ Failed to download image: {file_key} - {url}")


def fixstr(str, n=80):
    """
    if str is longer than n, return first n characters
    if str is shorter than n, return str with spaces added to end
    """
    if len(str) > n:
        return str[:n]
    else:
        return str + " " * (n - len(str))


mb = 1024 * 1024


def optimize_image(path, out=None, max_size=1*mb, max_width=None, max_height=None):
    """
    Note: This only supports PNGs at the moment

    max_size: maximum size in bytes - pass None to skip this check
    max_width: maximum width in pixels - pass None to skip this check
    max_height: maximum height in pixels - pass None to skip this check

    If max_width or max_height is specified, the image will be resized again if necessary

    returns:
    - 0. True / False: whether the image was optimized
    - 1. The space saved in bytes
    - 2. The "A" width and height of the image
    - 3. The "new" width and height of the image
    - 4. The scale factor used to resize the image
    """
    # validate inputs
    if max_width == 0:
        max_width = None
    if max_height == 0:
        max_height = None
    # either max_size or max_width or max_height must be specified
    if max_size is None and max_width is None and max_height is None:
        raise ValueError(
            "Either max_size or max_width or max_height must be specified")

    if out is None:
        out = path

    optimization_data = read_image_optimization_metadata(path)
    ext = os.path.splitext(path)[1].lower()

    if ext == '.png':
        target_ext = 'png'
    elif ext == '.jpg' or ext == '.jpeg':
        target_ext = 'jpg'
    else:
        # not supported
        return False, 0, 0, 0, 0

    margin = 0.3
    try:
        # Open the image
        img = Image.open(path)

        if optimization_data is not None:
            a_size = optimization_data['size']['a']
            a_w, a_h = optimization_data['dimensions']['a']
        else:
            a_size = os.path.getsize(path)
            # current dimensions
            a_w, a_h = img.size

        new_size = (a_w, a_h)

        targetsize = max_size - \
            (margin * mb) if max_size is not None else float('inf')

        scale_factor_a = math.sqrt(
            targetsize / a_size) if max_size is not None and a_size > max_size else 1

        # If either max_width or max_height is specified, resize the image while preserving aspect ratio
        w_scale = max_width / a_w if max_width else float('inf')
        h_scale = max_height / a_h if max_height else float('inf')
        scale_factor_b = min(w_scale, h_scale)

        scale_factor = min(scale_factor_a, scale_factor_b)

        if scale_factor < 1:  # Only resize if new size is smaller
            new_size = (int(a_w * scale_factor), int(a_h * scale_factor))
            if new_size[0] == 0 or new_size[1] == 0:
                return False, 0, 0, 0, 0
            img = img.resize(new_size)

        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix=f'.{target_ext}', delete=False) as tmp:
            metadata = a_w, a_h, a_size
            if target_ext == 'png':
                img.save(tmp.name,
                         format='PNG',
                         optimize=True,
                         pnginfo=png_optimization_metadata(*metadata))
            elif target_ext == 'jpg':
                exif = img.getexif()
                # 0x9286 is the exif tag for user comment
                exif[0x9286] = jpg_optimization_metadata(*metadata)
                img.save(tmp.name,
                         format='JPEG',
                         optimize=True,
                         exif=exif)
            else:
                raise ValueError(f"Unsupported image format: {target_ext}")

            # double check if it actually got smaller
            if os.path.getsize(tmp.name) >= a_size:
                os.remove(tmp.name)
                return False, 0, (a_w, a_h), (a_w, a_h), 1
            # Remove the original file before moving the temporary file to the original filename
            os.remove(path)
            shutil.move(tmp.name, out)
        endsize = os.path.getsize(out)
        saved = a_size - endsize

        return True, saved, (a_w, a_h), new_size, scale_factor
    except Exception as e:
        log_error(f"☒ Error optimizing {path}: {e}", print=True)
        return False, 0, None, None, None


def read_image_optimization_metadata(path):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == '.png':
        return read_png_optimization_metadata(path)
    elif ext == '.jpg' or ext == '.jpeg':
        return read_jpg_optimization_metadata(path)
    else:
        return None
        # raise ValueError(f"Unsupported file extension: {ext}")


def png_optimization_metadata(aW, aH, aS):
    metadata = PngInfo()
    # save compressed text info
    # AD stands for "A dimensions - original dimensions"
    metadata.add_text('AD', f'{aW}x{aH}')
    # AS stands for "A size - original size in bytes"
    metadata.add_text('AS', f'{aS}')
    return metadata


def read_png_optimization_metadata(path):
    try:
        img = Image.open(path)
    except (UnidentifiedImageError, OSError) as e:
        log_error(f"☒ Error reading {path}: {e}", print=True)
        return None
    metadata = img.info
    aD = metadata.get('AD', None)
    aW = int(aD.split('x')[0]) if aD else None
    aH = int(aD.split('x')[1]) if aD else None
    aS = metadata.get('AS', None)
    aS = float(aS) if aS else None
    img.close()

    if aD is None:
        return None

    return {
        'dimensions': {
            'a': (aW, aH),
            'b': img.size,
        },
        'size': {
            'a': aS,
            'b': os.path.getsize(path),
        },
    }


def read_jpg_optimization_metadata(path):
    try:
        img = Image.open(path)
    except (UnidentifiedImageError, OSError) as e:
        log_error(f"☒ Error reading {path}: {e}", print=True)
        return None
    exif = img.getexif()
    # 0x9286 is the exif tag for user comment
    data = exif.get(0x9286, None)
    img.close()
    try:
        data = json.loads(data)
        return {
            'dimensions': {
                'a': (data['AW'], data['AH']),
                'b': img.size,
            },
            'size': {
                'a': data['AS'],
                'b': os.path.getsize(path),
            },
        }
    except:
        return None


def jpg_optimization_metadata(aW, aH, aS):
    return json.dumps({
        'AW': aW,
        'AH': aH,
        'AS': aS,
    }, separators=(',', ':'))


def fetch_file_images(file_key, token):
    url = f"{API_BASE_URL}/files/{file_key}/images"
    headers = {"X-FIGMA-TOKEN": token}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError) as e:
        log_error(f"☒ Error fetching image fills: {e}", print=True)
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
    size = len(ids)

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
                tqdm.write(Fore.YELLOW +
                           f"☒ HTTP429 - Rate limit exceeded. ({max_retry} tries)")
                return {}

            # check if retry-after header is present
            retry_after = response.headers.get("retry-after")
            retry_after = int(
                retry_after) if retry_after else delay_between_429 * (retry + 1) * conncurrency

            if max_retry - retry < 2:
                # only show the last retry message
                tqdm.write(
                    Fore.YELLOW +
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
                    fixstr(f"{random.choice(emojis)} {fixstr(file_key, 8)} @{scale}x.{format} ({size})", 25))
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
            tqdm.write(Fore.RED + msg + Fore.RESET)
        logging.error(msg)
    except Exception as e:
        ...


def sync_metadata_for_hash_images(root_dir, src_dir, key):
    """
    syncs the meta.json file for the hash images
    """
    path: Path = Path(root_dir) / key / "images"
    if not path.exists():
        return

    document = read_file_data(Path(src_dir) / f"{key}.json")
    if not document:
        return

    metafile: Path = path / "meta.json"  # would be /:filekey/exports/meta.json
    files = [Path(file) for file in get_existing_images(path)]

    hashes = [file.stem for file in files]

    is_new = not metafile.exists()
    # save the info file
    with open(metafile, "w+") as f:
        try:
            olddata = json.load(f) if not is_new else {}
        except json.JSONDecodeError:
            olddata = {}

        images = {}
        optimization = {}
        dimensions = {}
        for hash_ in hashes:
            # hash : file
            file = [file for file in files if file.stem == hash_][0]
            ext = file.suffix
            images[hash_] = file.name
            data = read_image_optimization_metadata(path / file)
            if not data:
                continue

            d = data["dimensions"]
            s = data["size"]
            _ad = d['a']
            _bd = d['b']
            _as = s['a']
            _bs = s['b']
            _aw, _ah = _ad
            _bw, _bh = _bd
            dimensions[hash_] = [_aw, _ah]
            optimization[hash_] = {
                hash_: {
                    "dimensions": [_bw, _bh],
                    "saved": (_as - _bs if _as is not None and _bs is not None else None)
                }
            }

        data = {
            **olddata,
            # follows the figma-api format, "meta" key shall not be changed
            "document": {
                "version": document["version"],
                "lastModified": document["lastModified"]
            },
            # the last mod date of the meta file (a.k.a last archived)
            "archivedAt": datetime.now().isoformat(),
            # images map hash to file name
            "images": images,
            # original
            "dimensions": {
                # hash: [width, height]
                **dimensions
            },
            "optimization": {
                # hash: {
                #   dimensions: [width, height],
                #   saved: 0.0, # in bytes
                # }
                **optimization
            }
        }

        json.dump(data, f, separators=(',', ':'))
        f.close()


def sync_metadata_for_exports(root_dir, src_dir, key):
    """
    Saves the metadata under the root directory (of the file) to indicate which images are fulfilled.
    """

    path: Path = Path(root_dir) / key / "exports"
    if not path.exists():
        return

    document = read_file_data(Path(src_dir) / f"{key}.json")
    if not document:
        return

    metafile = path / "meta.json"  # would be /:filekey/exports/meta.json

    ids, depths, maxdepth = get_node_ids_and_depths(
        document, depth=None, include_canvas=True)  # get all ids

    # filter out only graphic files
    exports = get_existing_images(path)

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
    with open(metafile, "w") as f:
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
        log_error(f"File {file} not found", print=True)
        return None


def get_node_ids_and_depths(data, depth=None, include_canvas=False, types=None):
    """
    Returns a tuple of three lists:
    1. The IDs of the nodes.
    2. A dictionary that maps each ID to its depth in the tree.
    3. The maximum depth among all nodes.

    If `types` are specified, only nodes of those types are returned. Defaults to all types (None).
    """
    def extract_ids_recursively(node, current_depth):
        if depth is not None and current_depth > depth:
            return [], {}

        ids = []
        depth_map = {}

        if types is None or node["type"] in types:
            ids.append(node["id"])
            depth_map[node["id"]] = current_depth

        if "children" in node:
            for child in node["children"]:
                child_ids, child_depth_map = extract_ids_recursively(
                    child, current_depth + 1)
                ids.extend(child_ids)
                depth_map.update(child_depth_map)

        return ids, depth_map
    try:
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
        try:
            max_depth = max(depth_map.values())
        except ValueError:
            max_depth = 0

        return ids, depth_map, max_depth
    except (ValueError, TypeError):
        return [], {}, 0


def get_existing_images(images_dir):
    try:
        return set(filter_graphic_files(os.listdir(images_dir)))
    except FileNotFoundError:
        return set()


def get_node_dimensions(node):
    """
    Extract the width and height from a node's transformation matrix.

    Parameters:
    node: A document tree node.

    Returns:
    Tuple of width and height. (scale is applied to the original size)

    Note: this is not considered as "absolute" transform since it does not iterates through the parents' relativeTransform.
    """

    # Get the transformation matrix
    transform = node['relativeTransform']
    size = node['size']

    if transform is None or size is None:
        raise ValueError(
            f"Node {node.get('id')} is missing either relativeTransform or size")

    x = size['x']
    y = size['y']

    if x is None or y is None:
        raise ValueError(
            f"Node {node.get('id')} is missing either size.x or size.y")

    # The scaling factors are at positions [0][0] and [1][1]
    width_scale = transform[0][0]
    height_scale = transform[1][1]

    # The width and height are the scaling factors multiplied by the original size
    width = (width_scale if width_scale else 1) * size['x']
    height = (height_scale if height_scale else 1) * size['y']

    return width, height


def optimized_image_paint_map(paint_map, images: dict) -> dict[str, dict]:
    """
    Create a map that shows each hash image's usage in a document and the nodes that use it, along with the paint object.
    Plus, it also returns a "max" property for each hash image, which is the maximum size of the image used in the document.
    We can use max property to resize the image as so (if the original image is bigger than max), without losing quality.

    Parameters:
    node: A document tree node.
    images: A dictionary mapping image hashes to local directory path (original file, without any optimizations).
    """

    # TODO: validate this with testing
    def calculate_fit_size(nodesize, imgsize):
        """
        Calculate the size of the image when the scale mode is FIT.
        FIT means the image will be scaled up or down to fit within the size of the node, while maintaining the aspect ratio.
        """
        iw, ih = imgsize
        node_width, node_height = nodesize
        width_ratio = node_width / iw
        height_ratio = node_height / ih
        ratio = min(width_ratio, height_ratio)

        return iw * ratio, ih * ratio

    # TODO: validate this with testing
    def calculate_fill_size(nodesize, imgsize):
        """
        Calculate the size of the image when the scale mode is FILL.
        FILL means the image will be scaled up or down to cover the whole node, while maintaining the aspect ratio.
        """
        iw, ih = imgsize
        node_width, node_height = nodesize
        width_ratio = node_width / iw
        height_ratio = node_height / ih
        ratio = max(width_ratio, height_ratio)

        return iw * ratio, ih * ratio

    # TODO: validate this with testing
    def calculate_tile_size(imgsize, scaling_factor):
        """
        Calculate the size of the image when the scale mode is TILE.
        TILE means the image will be repeated across the node.
        """
        iw, ih = imgsize

        # For tiling, we need to ensure the size of the individual tile,
        # i.e., the image size after applying the scaling factor.
        tile_width = iw * scaling_factor
        tile_height = ih * scaling_factor

        return tile_width, tile_height

    # TODO: validate this with testing
    def calculate_stretch_size(imgsize, image_transform, rotation, relativeTransform):
        """
        Calculate the size of an image with the STRETCH scale mode.

        Parameters:
        node: A dictionary representing the node, with the keys "w" and "h" representing the width and height of the node, respectively.
        image_transform: A 2D array representing the affine transform applied to the image.
        rotation: A float representing the rotation of the image, in degrees.

        Returns:
        A tuple (width, height) representing the size of the image.
        """
        iw, ih = imgsize

        # Convert the image transform and relativeTransform to Numpy arrays.
        image_transform = np.array(image_transform)
        relativeTransform = np.array(relativeTransform)

        # Convert the rotation from degrees to radians.
        rotation = np.deg2rad(rotation)
        rotation_matrix = np.array([
            [np.cos(rotation), -np.sin(rotation)],
            [np.sin(rotation), np.cos(rotation)]
        ])

        # Compute inverse of the rotation_matrix
        inv_rotation_matrix = np.linalg.inv(rotation_matrix)

        # Combine the image transform with the rotation.
        image_transform_rotated = np.dot(
            image_transform[:, :2], rotation_matrix)
        image_transform_rotated = np.hstack(
            [image_transform_rotated, image_transform[:, 2, np.newaxis]])

        # the final transform - image_transform (rotation applied) * relativeTransform (node transform)
        transform = np.dot(image_transform_rotated[:, :2], inv_rotation_matrix)
        transform = np.hstack(
            [transform, image_transform_rotated[:, 2, np.newaxis]])

        # Apply the transform to the size of the node.
        rendersize = np.dot(transform[:, :2], [iw, ih])
        rw, rh = rendersize

        # The size might not be integer values after applying the transform, so we take the absolute value and round up to the nearest integer.
        width = np.ceil(np.abs(rw))
        height = np.ceil(np.abs(rh))

        return width, height

    for hash_image, info in paint_map.items():
        max_width = 0
        max_height = 0
        original_image_path = images[hash_image]

        # Read original image size
        try:
            with Image.open(original_image_path) as img:
                imgsize = img.size
                ow, oh = imgsize
        except (UnidentifiedImageError, OSError):
            log_error(f"Cannot read image {original_image_path}. Skipping...")
            continue

        for usage in info["usage"]:
            id = usage["id"]
            paint = usage["paint"]
            node = info["nodes"][id]
            # Note: this is not considered as "absolute" transform since it does not iterates through the parents' relativeTransform.
            relativeTransform = node["relativeTransform"]
            try:
                nodesize = get_node_dimensions(node)
            except ValueError as e:
                log_error(f'Invalid node value - {e}')
                continue

            scale_mode = paint["scaleMode"]

            if scale_mode == "FIT":
                width, height = calculate_fit_size(
                    nodesize=nodesize, imgsize=imgsize)
            elif scale_mode == "FILL":
                width, height = calculate_fill_size(
                    nodesize=nodesize, imgsize=imgsize)
            elif scale_mode == "TILE":
                scaling_factor = paint["scalingFactor"]
                width, height = calculate_tile_size(
                    imgsize=imgsize, scaling_factor=scaling_factor)
            elif scale_mode == "STRETCH":
                image_transform = paint["imageTransform"]
                rotation = paint.get("rotation", 0)
                try:
                    width, height = calculate_stretch_size(
                        imgsize, image_transform, rotation, relativeTransform)
                except TypeError as e:
                    log_error(f'unable to get desired size - {e}')
                    continue
            else:
                raise ValueError(f"Unsupported scale mode: {scale_mode}")

            # Compare with original image size, we cannot have an image bigger than the original
            width = min(ow, width)
            height = min(oh, height)

            max_width = max(max_width, width)
            max_height = max(max_height, height)
            # print((max_width, max_height), imgsize,  nodesize, node, paint)
        info["max"] = {
            "width": max_width,
            "height": max_height,
        }

    return paint_map


def image_paint_map(node) -> dict:
    """
    Create a map that shows where each image hash is used in a document.

    Parameters:
    node: The current node in the document tree.

    Returns:
    A dictionary mapping each hash to a list of dictionaries, each containing the id, and the fill object of a node where the hash is used.
    """
    map = {}

    # If the node has fills, check them for image references
    if "fills" in node:
        for fill in node["fills"]:
            if "imageRef" in fill:
                # This fill includes an image reference, so we record this node
                if fill["imageRef"] not in map:
                    map[fill["imageRef"]] = {"usage": [], "nodes": {}}

                # Append usage and nodes if not already present
                map[fill["imageRef"]]["usage"].append(
                    {"id": node["id"], "paint": fill})
                if node["id"] not in map[fill["imageRef"]]["nodes"]:
                    map[fill["imageRef"]]["nodes"][node["id"]] = {
                        "type": node["type"],
                        "relativeTransform": node["relativeTransform"],
                        "size": node["size"],
                    }

    # Recurse into the children of this node, if it has any
    if "children" in node:
        for child in node["children"]:
            child_map = image_paint_map(child)
            # Merge the child's map into our map
            for hash, data in child_map.items():
                if hash not in map:
                    map[hash] = {"usage": [], "nodes": {}}

                # Merge usage and nodes lists
                map[hash]["usage"].extend(data["usage"])
                map[hash]["nodes"].update(data["nodes"])

    return map


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
    ".jpeg",
    ".gif"
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


def pbarpos(pos, index=0, margin=0, batch=1):
    """
    returns the position of the progress bar
    the pos starts from the bottom.
    """

    return BOTTOM_POSITION - ((index + margin) + (pos * batch))


# main
if __name__ == "__main__":
    main()
