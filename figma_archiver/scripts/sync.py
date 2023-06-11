###
# select targets from image archive directory with key list /:dir/:key/**/*
# python sync.py :dir :out --list=keys.txt
#
# Example usage:
# selects files from a archives to b archives
# python select.py a b --list=keys.txt --pattern='{key}.json'
# a, b - archive directories with [key].json
###


import os
import click
import shutil
from pathlib import Path
from tqdm import tqdm


@click.command()
@click.argument('a', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('b', type=click.Path(exists=False))
@click.option('--list', 'list_file', help='list file (txt, line separated) containing file keys - read & select from [dir]', required=True, type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--link', help='use symlink to sync files (default: False)', is_flag=True)
@click.option('--pattern', help='pattern to format key (default: {key})', default='{key}')
def main(a, b, list_file, link: bool, pattern: str):
    a = Path(a)
    b = Path(b)

    try:
        b.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        click.echo(f"🚨 '{b}' is not empty.")
        return

    # read lines (remove empty lines)
    target_keys = open(list_file, 'r').read().splitlines()
    target_keys = [k for k in target_keys if k != '']

    tqdm.write(
        f"📦 {len(target_keys)} (files or directories) to be synced from {a} to {b}.")

    success = 0
    for key in tqdm(target_keys):
        rkey = pattern.format(key=key)
        origin = a / rkey
        target = b / rkey
        # check if key exists in dir
        if origin.exists():
            # link to b
            if link:
                os.symlink(origin, target)
            # copy to b
            else:
                if origin.is_file():
                    shutil.copy(origin, target)
                elif origin.is_dir():
                    shutil.copytree(origin, target)
                else:
                    raise Exception(f"🚨 {origin} is not a file or directory")
            emoji = '🔗' if link else '📦'
            tqdm.write(f"{emoji} {origin} → {target}")
            success += 1
        else:
            tqdm.write(f"❌ {key}")

    print(f"📦 {success}/{len(target_keys)} files copied from '{a}' to '{b}'")


if __name__ == '__main__':
    main()
