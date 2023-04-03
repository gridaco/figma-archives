import json
from pathlib import Path
import random
import re
import click
from tqdm import tqdm
import os
import sys

# for easily importing utils
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils import is_text_not_empty, visit, flatten, extract_text


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
        with open(json_path, 'r') as data:
            data = json.load(data)
        document = data['document']
        toplayers = flatten([canvas['children']
                             for canvas in document['children']])

        root_elements[directory.name] = toplayers

    artifects_dir = Path('artifacts')
    artifects_dir.mkdir(exist_ok=True)

    # output the text layers' text content into one file
    with open(artifects_dir / 'texts.txt', 'w') as f:
        for id in tqdm(ids, desc="Text Layers"):
            texts = extract_text(root_elements[id])
            for text in texts:
                f.write(text + '\n')
        f.close()

    # output the layers' name content into one file
    with open(artifects_dir / 'layer-names.txt', 'w') as f:
        for id in tqdm(ids, desc="Layer Names"):
            for layer in visit(root_elements[id], skip_types=['TEXT']):
                is_text_not_empty(layer['name']) and f.write(
                    layer['name'].strip() + '\n')
        f.close()

    with open(artifects_dir / 'layer-names-top.txt', 'w') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            for layer in visit(root_elements[id], skip_types=['TEXT'], max=0):
                is_text_not_empty(layer['name']) and f.write(
                    layer['name'].strip() + '\n')
        f.close()

    with open(artifects_dir / 'layer-names-top-frames.txt', 'w') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            for layer in visit(root_elements[id], visit_types=["FRAME"], max=0):
                is_text_not_empty(layer['name']) and f.write(
                    layer['name'].strip() + '\n')
        f.close()



if __name__ == '__main__':
    main()
