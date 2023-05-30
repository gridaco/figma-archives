###
### select targets from image archive directory with key list /:dir/:key/**/*
### python sync.py :dir :out --list=keys.txt
###


import click
import shutil
from pathlib import Path
from tqdm import tqdm

@click.command()
@click.argument('dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('out', type=click.Path(file_okay=False, dir_okay=True))
@click.option('--list', 'list_file', help='list file (txt, line separated) containing file keys - read & select from [dir]', required=True, type=click.Path(exists=True, file_okay=True, dir_okay=False))
def main(dir, out, list_file):
    dir = Path(dir)
    out = Path(out)

    try:
      out.mkdir(parents=True, exist_ok=True)
      # validate out is empty
      if len(list(out.iterdir())) > 0:
        raise FileExistsError
    except FileExistsError:
      print(f"🚨 '{out}' is not empty.")
      return
    
    # read lines (remove empty lines)
    target_keys = open(list_file, 'r').read().splitlines()
    target_keys = [k for k in target_keys if k != '']

    for key in tqdm(target_keys):
      # check if key exists in dir
      if Path(dir / key).exists():
        # copy to out
        shutil.copytree(dir / key, out / key)
        tqdm.write(f"📦 {key}")
      else:
        tqdm.write(f"❌ {key}")
    
    print(f"📦 {len(target_keys)} files copied from '{dir}' to '{out}'")

if __name__ == '__main__':
    main()
