import os
from pathlib import Path
from tqdm import tqdm
from PIL import Image, UnidentifiedImageError
import click


@click.command()
@click.argument('search_dir', type=click.Path(exists=True))
@click.option('--min', default=1, help='Minimum image size')
@click.option('--dry-run', is_flag=True, help='Dry run')
def main(search_dir, min, dry_run):
    search_dir = Path(search_dir)
    # Define the directory pattern to match
    dir_pattern = '**/images'

    # Define the file extensions to match
    extensions = ['.png', '.jpg']

    # Iterate over all directories that match the pattern
    for dir in tqdm(search_dir.glob(dir_pattern)):
        if dir.is_dir():
            # Iterate over all files in the directory with the specified extensions
            files = os.listdir(dir)
            files = [os.path.join(dir, f)
                     for f in files if os.path.splitext(f)[1] in extensions]

            for file in files:
                file = Path(file)
                try:
                    # Open the image and get its size
                    with Image.open(file) as img:
                        width, height = img.size

                    # If the image size is 1x1, delete the file
                    if width <= min or height <= min:
                        not dry_run and file.unlink()
                        tqdm.write(
                            f'Deleted {file} - reason: {width}x{height} image')
                except (UnidentifiedImageError, OSError):
                    # If the file is not an image, delete it
                    not dry_run and file.unlink()
                    tqdm.write(f'Deleted {file} - reason: not an image')
                except Exception as e:
                    tqdm.write(f'Error processing file {file}: {e}')


if __name__ == '__main__':
    main()
