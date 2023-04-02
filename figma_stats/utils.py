
def is_text_not_empty(text):
    return text is not None and len(text.strip()) > 0


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


def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
