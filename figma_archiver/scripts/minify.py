import jsonlines
import json
import click
import random
from tqdm import tqdm
from pathlib import Path
from urllib.parse import urlsplit


def minify_json_file(input_file_path: Path, output_file_path: Path):
    is_replacing = input_file_path.resolve().samefile(output_file_path.resolve())
    try:
        with input_file_path.open('r') as input_file:
            # if the input and output are the same (replace), create a tmp file called {input_file_path}.tmp
            # then rename it to {input_file_path} after it's done, after removing the original file
            if is_replacing:
              tmp_file_path = input_file_path.with_suffix('.tmp')
              # write tmp file
              with tmp_file_path.open('w') as output_file:
                  data = json.load(input_file)
                  json.dump(data, output_file, separators=(',', ':'))
              # remove original file
              input_file_path.unlink()
              # rename tmp file to original file
              tmp_file_path.rename(input_file_path)
            else:
                with output_file_path.open('w') as output_file:
                    data = json.load(input_file)
                    json.dump(data, output_file, separators=(',', ':'))
    except KeyboardInterrupt:
        if not is_replacing:
          tmp_file_path.unlink(missing_ok=True)
          tqdm.write("Keyboard interrupt detected. Removing incomplete output file.")
        raise
    except Exception as e:
        if not is_replacing: output_file_path.unlink(missing_ok=True)
        raise e
    finally:
        # it can cause loss of original file if interrupted
        # if .tmp file found and input_file_path not found, rename .tmp file to input_file_path
        if is_replacing and not input_file_path.exists() and tmp_file_path.exists():
            tmp_file_path.rename(input_file_path)
            tqdm.write(f"Restoring .tmp file to original file. {input_file_path}")


DEFAULT_OUTPUT_PATTERN = '{key}.json'


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--index-dir', default=None, required=False, help='Optional directory containing index.json file and map.json used for sorting the files.', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--pattern', default='*.json', help='Pattern to look for JSON files.')
@click.option('--output', default=None, help='Output directory. If not specified, use the input directory.')
@click.option('--output-pattern', required=False, default=DEFAULT_OUTPUT_PATTERN, help='Pattern for the output file.')
@click.option('--max', default=None, type=int, help='Maximum number of items to process.')
@click.option('--shuffle', is_flag=True, help='Shuffle the target files for even distribution.')
def minify_json_directory(input_dir, index_dir, pattern, output, output_pattern, max, shuffle):
    input_dir = Path(input_dir)
    if not output:
        output = input_dir
    else:
        output = Path(output)

    output.mkdir(parents=True, exist_ok=True)
    json_files = sorted(list(input_dir.glob(pattern)))

    # Check for minified files
    # check if there are already minified files (if the parent path is different)
    # if the parent path is the same, we will check if the file has been minified, in the main loop
    # to be more accurate, we actually have to check the patterns as well, but for simplicity, we will just check the parent path, otherwise, let it handle in the main loop
    if input_dir.resolve().samefile(output.resolve()):
        minified_files = set()
        if output_pattern == DEFAULT_OUTPUT_PATTERN: ...
        else: ...
    else:
      search_pattern = output_pattern.format(key="*")
      minified_files = set(output.rglob(search_pattern))
    
    minified_files = {f.stem for f in minified_files}

    if index_dir:
        json_files = sort_with_index(json_files=json_files, index_dir=index_dir)

    if shuffle:
        random.shuffle(json_files)

    json_files = [f for f in json_files if f.stem not in minified_files]
    if max is not None:
        json_files = json_files[:max]

    total_saved_space = 0
    with tqdm(json_files, desc='📦') as progress:
      for file_path in progress:
          start_size = file_path.stat().st_size

          already_minified = False
          file_key = file_path.stem
          output_file_name = Path(output_pattern.format(key=file_key))
          output_file_path = output / output_file_name

          # check if input and output are same (overwrite)
          if output_file_path.exists() and file_path.resolve().samefile(output_file_path.resolve()):
              # check if the output file has been minified, by checking if it has only one line
              with output_file_path.open('r') as f:
                  if len(f.readlines()) == 1:
                      # skip this file
                      already_minified = True

          if already_minified:
              tqdm.write(f"📦 Skipping {output_file_name} (already minified)")
          else:
              output_file_path.parent.mkdir(parents=True, exist_ok=True)

              minify_json_file(file_path, output_file_path)
              saved_space = start_size - output_file_path.stat().st_size
              saved_space_mb = saved_space / (1024 * 1024)
              total_saved_space += saved_space_mb
              tqdm.write(f"📦 Saved {saved_space_mb:.2f} MB for {output_file_name}")
              progress.desc = f"📦 Saved {(total_saved_space / 1024):.2f} GB"


def sort_with_index(json_files, index_dir):
    """
    The arguments and how it is used
    - index_dir - contains a index.json and map.json
    - index.json - a jsonl file containing the objects with "id" and "link" of the community file
    - map.json - a json file containing the mapping of the {community-file-link : drafted-file-url} # we can extract the id from the link and url with parse_id
    - json_files - the list of input json files as a list of path, format: ./a/b/.../{id}.json

    The sorting
    1. get the list of ids from index.json
    2. get the mapping of id to filekey from map.json
    3. sort the mapping based on the order of ids in index.json
    4. sort the json_files based on the order of filekeys sorted mapping (3)

    As a result, the json_files will be sorted based on the order of ids in index.json (where the json_files did not have access to original file order in the index)
    """

    raise NotImplementedError("This function is not implemented yet")

    # make sure index.json and map.json exists
    index_dir = Path(index_dir)
    index_file = index_dir / 'index.json'
    map_file = index_dir / 'map.json'
    if not index_file.exists() or not map_file.exists():
        raise Exception(f"index.json or map.json not found in {index_dir}")
    
    with jsonlines.open(index_dir / 'index.json') as reader:
        index_ids = [x['id'] for x in reader]
         # Sort the files based on the index
        with map_file.open('r') as f:
            map_data = json.load(f)
            # Parse and remake the map
            map_data = {parse_id(k): parse_id(v) for k, v in map_data.items()}

            # Reverse the map_data to have file keys as keys and community IDs as values
            map_data = {v: k for k, v in map_data.items()}

            # Create a dictionary to map file keys to json_files
            file_key_to_json_file = {f.stem: f for f in json_files}

            # Sort the json_files based on the order of index_ids
            sorted_json_files = [
                file_key_to_json_file[map_data[id]] for id in index_ids if id in map_data
            ]
            
            return sorted_json_files



def parse_id(url):
    """
    parse the id from both community link and file url
    https://www.figma.com/..xxxx/file/:id

    This will only work for cleaned url.
    """
    result = urlsplit(url)
    return Path(result.path).name

if __name__ == '__main__':
    minify_json_directory()
