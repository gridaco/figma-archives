from urllib.parse import urlparse
import json
import shutil
from pathlib import Path
import click
from tqdm import tqdm
import jsonlines


@click.command()
@click.option('--index', required=True, type=click.Path(exists=True), help='Path to index file (JSONL)')
@click.option('--map', required=True, type=click.Path(exists=True), help='Path to map file (JSON)')
@click.option('--meta', required=True, type=click.Path(exists=True), help='Path to meta file (JSON)')
@click.option('--output', required=True, type=click.Path(), help='Path to output directory')
@click.option('--dir-files-archive', required=True, type=str, help='Path to files archive directory')
@click.option('--dur-images-archive', required=True, type=str, help='Path to images archive directory')
@click.option('--sample', default=None, type=int, help='Number of samples to process')
@click.option('--sample-all', is_flag=False, help='Process all available data')
def main(index, map, meta, output, dir_files_archive, dir_images_archive, sample, sample_all):
    # Read index file
    with jsonlines.open(index, mode='r') as reader:
        # get id, link, title
        index_data = [(obj["id"], obj["link"], obj["title"]) for obj in reader]

    # Read map file
    with open(map, 'r') as f:
        map_data = json.load(f)

    # Read meta file
    with open(meta, 'r') as f:
        meta_data = json.load(f)

    dir_files_archive = Path(dir_files_archive)
    dir_images_archive = Path(dir_images_archive)

    # create root output dir
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    # locate the already-sampled files with finding map.json files
    # get the ids of the already-sampled files
    completes = [x.parent.name for x in output.glob('**/map.json')]

    # pre-validate the targtes (check if drafted file exists for community lunk)
    available = [(id, link) for id, link in index_data
                 if map_data[link] is not None]

    # remove the already-sampled files from the available list
    available = [x for x in available if x[0] not in completes]

    # Calculate sample size
    if sample_all:
        sample_size = len(available)
    else:
        sample_size = sample if sample is not None else len(available)

    targets = available[:sample_size]

    # Process samples with tqdm progress bar
    for id, link, title in tqdm(targets, desc='🗳️'):
        try:
            file_url = map_data[link]

            file_key = extract_file_key(file_url)
            output_dir: Path = output / id

            tqdm.write(f"☐ {file_key}")

            # If the output directory already exists, remove it and create a new one
            if output_dir.exists():
                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=False, exist_ok=False)

            # Copy file.json
            shutil.copy(dir_files_archive /
                        f"{file_key}.json", output_dir / "file.json")

            # Copy images
            shutil.copytree(dir_images_archive / file_key,
                            output_dir / "images")

            # Write meta.json
            with open(output_dir / "meta.json", "w") as f:
                json.dump(meta_data[id], f)

            # Write map.json
            with open(output_dir / "map.json", "w") as f:
                json.dump({"latest": meta_data[id]["version"], "versions": {
                          meta_data[id]["version"]: file_key}}, f)

            tqdm.write(f"☑️ {file_key}")
        except Exception as e:
            tqdm.write(f"☒ {file_key} - Error sampleing <{title}>")


def extract_file_key(url):
    """
    Extracts the file key from a Figma file URL.

    For example, if the file url is "https://www.figma.com/file/ckoLxKa4EKf3CaPq609rpa/Material-3-Design-Kit-(Community)?t=VSv529MHpDOG6ZmU-0"

    After splitting the path with the / delimiter, the resulting list is
    ['', 'file', 'ckoLxKa4EKf3CaPq609rpa', ...].
    The file key is at index [2] (the third element) in the list.
    """
    path = urlparse(url).path
    file_key = path.split('/')[2]
    return file_key


if __name__ == '__main__':
    main()
