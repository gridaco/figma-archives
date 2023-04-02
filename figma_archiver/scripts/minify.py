import json
import click
import ijson
import random
from tqdm import tqdm
from pathlib import Path


def minify_json_file(input_file_path, output_file_path):
    try:
        with input_file_path.open('r') as input_file, output_file_path.open('w') as output_file:
            parser = ijson.parse(input_file)
            json.dump({k: v for k, v in parser if not isinstance(
                v, ijson.common.JSONError)}, output_file, separators=(',', ':'))
    except Exception as e:
        output_file_path.unlink(missing_ok=True)
        raise e


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--pattern', default='*.json', help='Pattern to look for JSON files.')
@click.option('--output', default=None, help='Output directory. If not specified, use the input directory.')
@click.option('--output-pattern', default='{key}.min.json', help='Pattern for the output file.')
@click.option('--max', default=None, type=int, help='Maximum number of items to process.')
@click.option('--shuffle', is_flag=True, help='Shuffle the target files for even distribution.')
def minify_json_directory(input_dir, pattern, output, output_pattern, max, shuffle):
    input_dir = Path(input_dir)
    if not output:
        output = input_dir
    else:
        output = Path(output)

    json_files = list(input_dir.glob(pattern))

    # Check for minified files
    search_pattern = output_pattern.format(key="*")
    minified_files = set(output.rglob(search_pattern))
    minified_files = {f.stem for f in minified_files}
    json_files = [f for f in json_files if f.stem not in minified_files]

    if shuffle:
        random.shuffle(json_files)

    if max is not None:
        json_files = json_files[:max]

    for file_path in tqdm(json_files, desc='Minifying JSON files'):
        file_key = file_path.stem
        output_file_name = Path(output_pattern.format(key=file_key))
        output_file_path = output / output_file_name

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        minify_json_file(file_path, output_file_path)
        saved_space = file_path.stat().st_size - output_file_path.stat().st_size
        tqdm.write(f"Saved {saved_space} bytes for {output_file_name}")


if __name__ == '__main__':
    minify_json_directory()
