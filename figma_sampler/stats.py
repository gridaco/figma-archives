import json
from pathlib import Path
import random
import re
import click
from tqdm import tqdm


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
                isvalid(layer['name']) and f.write(
                    layer['name'].strip() + '\n')
        f.close()

    with open(artifects_dir / 'layer-names-top.txt', 'w') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            for layer in visit(root_elements[id], skip_types=['TEXT'], max=0):
                isvalid(layer['name']) and f.write(
                    layer['name'].strip() + '\n')
        f.close()

    with open(artifects_dir / 'layer-names-top-frames.txt', 'w') as f:
        for id in tqdm(ids, desc="Top Layer Names"):
            for layer in visit(root_elements[id], visit_types=["FRAME"], max=0):
                isvalid(layer['name']) and f.write(
                    layer['name'].strip() + '\n')

        f.close()


def extract_text(layers: list):
    """
    loop the layers recursively and extract the text layers' text content
    - if there is a 'children' key, call the function again
    - if layer type is 'TEXT', return the text content (text#characters)
    """

    texts = []

    for layer in visit(layers, visit_types=['TEXT']):
        if 'type' in layer and layer['type'] == 'TEXT':
            texts.append(layer['characters'])

    return texts


def visit(layers, skip_types=[], visit_types=None, max=None, depth=0):
    if max is not None and depth > max:
        return

    # if layers not list, wrap it in a list
    if not isinstance(layers, list):
        layers = [layers]

    for layer in layers:
        if visit_types is not None:
            if 'type' in layer and layer['type'] in visit_types:
                yield layer
        elif 'type' in layer and layer['type'] not in skip_types:
            yield layer

        if 'children' in layer:
            yield from visit(layer['children'], skip_types=skip_types, visit_types=visit_types, max=max, depth=depth + 1)


def isvalid(text):
    return text is not None and len(text.strip()) > 0


def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


if __name__ == '__main__':
    main()
