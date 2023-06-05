import json
import os
import random
import re
import sys
import threading
import warnings
from pathlib import Path

import click
from tqdm import tqdm

# for easily importing utils
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from stats_util import extract_text, flatten, is_text_not_empty, visit


@click.command()
@click.argument('samples', type=click.Path(exists=True), required=True)
@click.option('--max', type=click.INT, default=None, required=False)
@click.option('--shuffle', is_flag=True, type=click.BOOL, default=False, required=False)
def main(samples, max, shuffle):
    samples = Path(samples)

    # list directories in samples
    directories = [d for d in samples.iterdir() if d.is_dir()]

    # Cut the list if max is specified
    if max:
        directories = directories[:max]

    # Shuffle the list if shuffle is specified
    if shuffle:
        directories = random.shuffle(directories)

    ids = [d.name for d in directories]

    root_elements = {}

    for directory in tqdm(directories, desc='Indexing..', leave=False):
        # get the text layers' json file
        json_path = directory / 'file.json'
        try:
            with open(json_path, 'r') as file:
                data = json.load(file)
                # print(json.dumps(data, indent=4))
            document = data['document']
            toplayers = [child for canvas in document['children'] for child in canvas['children']]
            root_elements[directory.name] = toplayers
        except FileNotFoundError as e:
            print(f"Error: {e}. Skipping directory {directory}")
    print('PRINT:----Indexing done!-------')

    artifects_dir = Path('artifacts')
    artifects_dir.mkdir(exist_ok=True)

    # output the text layers' text content into one file
    with open(artifects_dir / 'texts.txt', 'w') as f:
        for id in tqdm(ids, desc="Text Layers"):
            try:
                texts = extract_text(root_elements[id])
                for text in texts:
                    f.write(text + '\n')
            except Exception as e:
                print(f"Error processing id {id}: {e}")
                continue
        f.close()
    print('PRINT:Texts extracted!')

    # output the layers' name content into one file
    with open(artifects_dir / 'layer-names.txt', 'a') as f:
        for id in tqdm(ids, desc="Layer Names"):
            try:
                for layer in visit(root_elements[id], skip_types=['TEXT']):
                    if is_text_not_empty(layer['name']):
                        f.write(layer['name'].strip() + '\n')
            except KeyError as e:
                print(f"Error processing id {id}: key {e} not found")
                continue
        f.close()
    print('PRINT:Layer names extracted!')

    with open(artifects_dir / 'layer-names-top.txt', 'a') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            try:
                for layer in visit(root_elements[id], skip_types=['TEXT'], max=0):
                    if is_text_not_empty(layer['name']):
                        f.write(layer['name'].strip() + '\n')
            except KeyError as e:
                print(f"Error processing id {id}: key {e} not found")
                continue
        f.close()
    print('Top layer names extracted!')

    with open(artifects_dir / 'layer-names-top-frames.txt', 'a') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            try:
                for layer in visit(root_elements[id], visit_types=["FRAME"], max=0):
                    if is_text_not_empty(layer['name']):
                        f.write(layer['name'].strip() + '\n')
            except KeyError as e:
                print(f"Error processing id {id}: key {e} not found")
                continue
        f.close()
    print('Top layer frames names extracted!')


if __name__ == '__main__':
    main()
