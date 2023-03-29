import click
import os
import shutil
from tqdm import tqdm


@click.command()
@click.option('--dir', default='.', help='Directory to process JSON files and create subdirectories.')
def process_json_files(dir):
    """
    Process JSON files in the given directory.
    The directory manipulated by files.py has a single directory with json files under it.
    This script alts the directory structure from

    A:
      - a.json
      - b.json

    To

    B:
      - a/
        - a.json
        - images/
      - b/
        - b.json
        - images/

    """
    json_files = [file_name for file_name in os.listdir(
        dir) if file_name.endswith('.json')]

    for file_name in tqdm(json_files, desc="Processing JSON files", unit="file"):
        if file_name.endswith('.json'):
            key = file_name[:-5]  # Remove .json extension to get the key
            new_dir = os.path.join(dir, key)
            new_file_path = os.path.join(new_dir, file_name)
            images_dir = os.path.join(new_dir, 'images')

            if not os.path.exists(new_dir):
                os.makedirs(new_dir)

            if not os.path.exists(images_dir):
                os.makedirs(images_dir)

            # Move the JSON file to the new directory
            shutil.move(os.path.join(dir, file_name), new_file_path)

            tqdm.write(f"Processed {file_name} in {new_dir}")


if __name__ == '__main__':
    process_json_files()
