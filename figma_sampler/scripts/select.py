###
# selects files from a archives to b archives
# python select.py a b --list=keys.txt
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
@click.option('--list', 'list_file', help='list file (txt, line separated) containing file keys - read & select from [a]', required=True, type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--link', help='use symlink to sync files (default: False)', is_flag=True)
def main(a, b, list_file, link):
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

    tqdm.write(f"📦 {len(target_keys)} files to be copied from {a} to {b}.")

    success = 0
    for key in tqdm(target_keys):
        origin = a / f"{key}.json"
        target = b / f"{key}.json"
        # check if key exists in a
        if origin.exists():
            if link:
                # link to b
                os.symlink(origin, target)
            else:
                # copy to b
                shutil.copy(origin, target)
            tqdm.write(f"📦 {origin} → {target}")
            success += 1
        else:
            tqdm.write(f"❌ {key}.json")

    msg = f"📦 {success}/{len(target_keys)} files copied from '{a}' to '{b}'"
    # tqdm.write(msg)
    print(msg)


if __name__ == '__main__':
    main()
