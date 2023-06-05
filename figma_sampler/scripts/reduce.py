from pathlib import Path
from tqdm import tqdm
import shutil
import random
import click


@click.command()
@click.argument('samples_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--to', help='Number of target to be reduced as', required=True, type=int)
def main(samples_dir, to):
    # list all directories under samples_dir
    dirs = [d for d in Path(samples_dir).iterdir() if d.is_dir()]

    # count the item to be removed
    to_remove = len(dirs) - int(to)

    # randomly remove the directories
    for d in tqdm(random.sample(dirs, to_remove), leave=True):
        shutil.rmtree(d)
        tqdm.write(f"🗑️ {d}")

    tqdm.write(f"🗑️ {to_remove} directories removed, {to} directories left.")


if __name__ == '__main__':
    main()
