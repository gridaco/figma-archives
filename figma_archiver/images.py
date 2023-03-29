import click
import json
import os
import re
import requests
import multiprocessing
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from itertools import chain

load_dotenv()

API_BASE_URL = "https://api.figma.com/v1"


def read_file_data(file_key):
    with open(os.path.join(file_key, f"{file_key}.json")) as f:
        return json.load(f)


def get_node_ids(data, depth=None):
    def extract_ids_recursively(node, current_depth):
        if depth is not None and current_depth > depth:
            return []

        ids = [node["id"]]
        if "children" in node:
            for child in node["children"]:
                ids.extend(extract_ids_recursively(child, current_depth + 1))
        return ids

    return [
        id_
        for child in data["document"]["children"]
        for id_ in extract_ids_recursively(child, 0)
    ]


def get_existing_images(images_dir):
    return set(os.listdir(images_dir))


def download_image(url, output_path):
    response = requests.get(url)
    with open(output_path, "wb") as f:
        f.write(response.content)


def fetch_and_save_images(url_and_path_pairs):
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        for _ in tqdm(
            executor.map(lambda x: download_image(*x), url_and_path_pairs),
            total=len(url_and_path_pairs),
        ):
            pass


def fetch_images_b(file_key, token):
    url = f"{API_BASE_URL}/files/{file_key}/images"
    headers = {"X-FIGMA-TOKEN": token}
    response = requests.get(url, headers=headers)
    data = response.json()

    if "error" in data and data["error"]:
        raise ValueError("Error fetching image fills")

    return data["meta"]["images"]


def fetch_images_a(file_key, ids, scale, format, token):
    ids_chunk_size = 50
    num_workers = 5
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

    def fetch_images_chunk(chunk):
        params["ids"] = ",".join(chunk)
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if "err" in data and data["err"]:
            raise ValueError("Error fetching layer images")
        return data["images"]

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        image_urls = dict(
            chain.from_iterable(
                tqdm(executor.map(fetch_images_chunk, ids_chunks)))
        )

    return image_urls


@click.command()
@click.argument("dir")
@click.option("--fmt", default="png", help="Image format to bake the layers")
@click.option("--s", default="1", help="Image scale")
@click.option("--depth", default=None, help="Layer depth to go recursively")
@click.option("-t", "--figma-token", help="Figma API access token.", default=os.getenv("FIGMA_ACCESS_TOKEN"), type=str)
@click.option("--src", default="{filekey}.json", help="Path to the JSON file")
def main(dir, fmt, s, depth, figma_token, src):
    root_dir = Path(dir)
    subdirs = [subdir for subdir in root_dir.iterdir() if subdir.is_dir()]

    for subdir in tqdm(subdirs, desc="Directories"):
        key = subdir.name

        if os.path.isabs(src):
            json_file = Path(src.format(filekey=key))
        else:
            json_file = subdir / src.format(filekey=key)

        if json_file.is_file():
            tqdm.write(f"Processing directory {subdir}")

            with open(json_file, "r") as file:
                file_data = json.load(file)

            if depth is not None:
                depth = int(depth)

            node_ids = get_node_ids(file_data, depth)

            images_dir = subdir / "images"
            existing_images = os.listdir(images_dir)

            # Fetch and save image fills (B)
            if not any(not re.match(r"\d+:\d+", img) for img in existing_images):
                tqdm.write("Fetching image fills...")
                image_fills = fetch_images_b(key, token=figma_token)
                url_and_path_pairs = [
                    (url, os.path.join(images_dir, f"{hash_}.{fmt}"))
                    for hash_, url in image_fills.items()
                ]
                fetch_and_save_images(url_and_path_pairs)
            else:
                tqdm.write("Image fills already fetched")

            # Fetch and save layer images (A)
            node_ids_to_fetch = [
                node_id
                for node_id in node_ids
                if f"{node_id}.{fmt}" not in existing_images
                and f"{node_id}@{s}x.{fmt}" not in existing_images
            ]

            if node_ids_to_fetch:
                tqdm.write("Fetching layer images...")
                layer_images = fetch_images_a(
                    key, node_ids_to_fetch, s, fmt, token=figma_token)
                url_and_path_pairs = [
                    (
                        url,
                        os.path.join(
                            images_dir,
                            f"{node_id}{'@' + str(s) + 'x' if s != '1' else ''}.{fmt}",
                        ),
                    )
                    for node_id, url in layer_images.items()
                ]
                fetch_and_save_images(url_and_path_pairs)
            else:
                tqdm.write("Layer images already fetched")

            tqdm.write("All images fetched and saved successfully")
        else:
            tqdm.write(
                f"Skipping directory {subdir}: JSON file not found at '{json_file}'")


if __name__ == "__main__":
    main()
