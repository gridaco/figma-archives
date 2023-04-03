import click
import shutil
import os
import random
from tqdm import tqdm
import os
from pathlib import Path
from fnmatch import fnmatch

@click.command()
@click.argument("dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--max", default=None, type=int, help="Maximum number of items to process.")
@click.option('-o', "--out", required=True, type=click.Path(), help="The out dir")
@click.option('--depth', default=None, type=int, help="Depth to copy the directory tree.")
def main(dir, out, max, depth):
    """
    Selects random samples from a directory, copies them to a new directory.
    """

    items = os.listdir(dir)
    dirs, files = [], []

    for item in items:
        item_path = os.path.join(dir, item)
        if os.path.isfile(item_path):
            files.append(item)
        elif os.path.isdir(item_path):
            dirs.append(item)
        else:
            raise ValueError(f"Unexpected item type at {item_path}")

    if not os.path.exists(out):
        os.makedirs(out)

    if max is not None and max > 0:
        max = min(max, len(dirs) + len(files))
        selected_items = random.sample(dirs + files, max)
    else:
        selected_items = dirs + files

    for item in tqdm(selected_items, desc="Re-sampling items", unit="item"):
        src = os.path.join(dir, item)
        dst = os.path.join(out, item)

        if os.path.isfile(src):
            shutil.copy(src, dst)
        elif os.path.isdir(src):
            copytree(src, dst, max_depth=depth)  # Use the custom copytree function
        else:
            raise ValueError(f"Unexpected item type at {src}")


def include_by_depth(src, names, max_depth):
    if max_depth is None:
        return []

    current_depth = src.count(os.path.sep) - base_src_depth
    ignore_list = []

    if current_depth >= max_depth - 1:
        for name in names:
            if os.path.isdir(os.path.join(src, name)):
                ignore_list.append(name)

    return ignore_list

def copytree(src, dst, max_depth=None, symlinks=False, ignore=None):
    global base_src_depth
    base_src_depth = src.count(os.path.sep)

    if ignore is None:
        ignore_func = lambda src, names: include_by_depth(src, names, max_depth)
    else:
        def ignore_func(src, names):
            return ignore(src, names) + include_by_depth(src, names, max_depth)

    shutil.copytree(src, dst, symlinks=symlinks, ignore=ignore_func)


if __name__ == '__main__':
    main()
