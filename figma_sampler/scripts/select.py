###
### selects files from a archives to b archives
### python select.py a b --list=keys.txt
### a, b - archive directories with [key].json
###

import click
import shutil
from pathlib import Path

@click.command()
@click.argument('a', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('b', type=click.Path(exists=False))
@click.option('--list', 'list_file', help='list file (txt, line separated) containing file keys - read & select from [a]', required=True, type=click.Path(exists=True, file_okay=True, dir_okay=False))
def main(a, b, list_file):
    a = Path(a)
    b = Path(b)

    try:
      b.mkdir(parents=True, exist_ok=True)
      # validate b is empty
      if len(list(b.iterdir())) > 0:
        raise FileExistsError
    except FileExistsError:
      print(f"🚨 '{b}' is not empty.")
      return

    # read lines (remove empty lines)
    target_keys = open(list_file, 'r').read().splitlines()
    target_keys = [k for k in target_keys if k != '']

    # tqdm.write(f"📦 {len(target_keys)} files to be copied from {a} to {b}.")

    success = 0
    # select files with target_keys
    # pbar = tqdm(total=len(target_keys))
    
    for key in target_keys: #tqdm():
      # check if key exists in a
      if Path(a / f"{key}.json").exists():
        # copy to b
        shutil.copy(a / f"{key}.json", b / f"{key}.json")
        # tqdm.write(f"📦 {key}.json")
        success += 1
      else:
         ...
        # tqdm.write(f"❌ {key}.json")
      # pbar.update(1)
    
    msg = f"📦 {success}/{len(target_keys)} files copied from '{a}' to '{b}'"
    # tqdm.write(msg)
    print(msg)

if __name__ == '__main__':
    main()