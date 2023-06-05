
import json
from .utils import getfrom


def roots_from_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
        roots = []
        for canvas in data["document"]["children"]:
            for root in canvas["children"]:
                roots.append((root, canvas['id']))

        return roots


def process_node(node: dict, depth, canvas, parent=None, current_depth=0):
    """
    if depth is None, it means we want to process all nodes
    """

    id = node["id"]

    # Process the node and return the organized object
    if depth is not None and current_depth > depth:
        return

    if 'children' in node:
        for child in node['children']:
            yield from process_node(node=child, depth=depth, parent=node, canvas=canvas, current_depth=current_depth+1)

    try:
        record = {}

        # switch-case types
        _type = node['type']

        # geometry
        record = {
            **record,
            'x_abs': getfrom(node, "absoluteBoundingBox", "x", default=0),
            'y_abs': getfrom(node, "absoluteBoundingBox", "y", default=0),
            'rotation': getfrom(node, 'rotation', default=0),
        }
        if 'relativeTransform' in node:
            # size and relativeTransform is only present if geometry=paths is passed
            # https://github.com/gridaco/design-sdk/blob/main/figma-remote/lib/blenders/general.blend.ts
            x = getfrom(node, "relativeTransform", 0,
                        2, default=0) if parent else 0
            y = getfrom(node, "relativeTransform", 1,
                        2, default=0) if parent else 0
            width = getfrom(node, "size", "x")
            height = getfrom(node, "size", "y")
        else:
            x = absrel(node, parent, 'x') if parent else 0
            y = absrel(node, parent, 'y') if parent else 0
            width = getfrom(node, "absoluteBoundingBox", "width")
            height = getfrom(node, "absoluteBoundingBox", "height")

        # box-shadow
        box_shadow = zip_box_shadow(node)

        color = zip_color(node)
        background_color = zip_background_color(node)

        record = {
            **record,
            'color': color and hex8(color) if _type == 'TEXT' else None,
            'background_color': background_color and hex8(background_color) if _type != 'TEXT' else None,
            'background_image': zip_background_image(node),
            'border_color': hex8(zip_color(node, p='strokes')),
        }

        # general
        record = {
            **record,
            'node_id': node['id'],
            'parent_id': parent['id'] if parent else None,
            'canvas_id': canvas,
            'type': _type,
            'name': node['name'],
            'visible': node.get('visible', True),
            'depth': current_depth,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'opacity': node.get('opacity', 1),

            'fills': node.get('fills'),
            'effects': node.get('effects'),
            'strokes': node.get('strokes'),

            'stroke_linecap': node.get('strokeCap', None) if len(node.get('strokes', [])) > 0 else None,
            'border_alignment': node.get('strokeAlign', None) if len(node.get('strokes', [])) > 0 else None,
            'border_width': node.get('strokeWeight', None) if len(node.get('strokes', [])) > 0 else None,
            'border_radius': node.get('cornerRadius', None),

            'box_shadow_offset_x': getfrom(box_shadow, 'offset', 'x') if box_shadow else None,
            'box_shadow_offset_y': getfrom(box_shadow, 'offset', 'y') if box_shadow else None,
            'box_shadow_blur': getfrom(box_shadow, 'radius') if box_shadow else None,
            'box_shadow_color': getfrom(box_shadow, 'spread') if box_shadow else None,
            'box_shadow_color': getfrom(box_shadow, 'color') if box_shadow else None,

            'padding_top': node.get('paddingTop', None),
            'padding_left': node.get('paddingLeft', None),
            'padding_right': node.get('paddingRight', None),
            'padding_bottom': node.get('paddingBottom', None),

            # constraints
            'constraint_vertical': node.get('constraints', {}).get('vertical'),
            'constraint_horizontal': node.get('constraints', {}).get('horizontal'),

            'layout_align': node.get('layoutAlign'),
            'layout_mode': node.get('layoutMode'),
            'layout_positioning': node.get('layoutPositioning'),
            'layout_grow': node.get('layoutGrow'),
            'primary_axis_sizing_mode': node.get('primaryAxisSizingMode'),
            'primary_axis_align_items': node.get('primaryAxisAlignItems'),
            'counter_axis_sizing_mode': node.get('counterAxisSizingMode'),
            'counter_axis_align_items': node.get('counterAxisAlignItems'),
            'gap': node.get('itemSpacing'),
            'reverse': node.get('reverse'),

            'fill_geometry': node.get('fillsGeometry'),
            'stroke_geometry': node.get('strokesGeometry'),

            'transition_node_id': node.get('transitionNodeID'),
            'transition_duration': node.get('transitionDuration'),
            'transition_easing': node.get('transitionEasing'),

            'clips_content': node.get('clipsContent'),
            'is_mask': node.get('isMask'),
            'export_settings': zip_export_settings(node),
            'mix_blend_mode': None if node.get('blendMode') == 'PASS_THROUGH' else node.get('blendMode'),
            'aspect_ratio': (width / height if (height is not None and height > 0) else None) if node.get('preserveRatio') else None,
        }

        if _type == "TEXT":
            _style: dict = node.get('style')
            record = {
                **record,
                'characters': node.get('characters', ''),
                'font_family': _style.get('fontFamily'),
                'font_weight': _style.get('fontWeight'),
                'font_size': _style.get('fontSize'),
                'font_style': 'italic' if _style.get('italic') else None,
                'text_align': _style.get('textAlignHorizontal'),
                'text_align_vertical': _style.get('textAlignVertical'),
                'text_decoration': _style.get('textDecoration'),
                'text_auto_resize': _style.get('textAutoResize'),
                'letter_spacing': _style.get('letterSpacing'),
            }

            # remove style from record['data']
            try:
                del record['data']['style']
            except:
                ...

        # if the children is being handled, remove the 'children' from 'data' from record.
        if current_depth == depth:
            record['data'] = node
            # the last node in the depth
            ...
        else:
            # this node is parent to other nodes in the max depth
            if 'children' in node:
                record['data'] = {k: v for k,
                                  v in node.items() if k != 'children'}
                record['children'] = [child['id']
                                      for child in node['children']]
                record['n_children'] = len(node['children'])
            else:
                record['data'] = node

        # finally, safely remove all keys from record, from record['data'] to reduce the size of the record.
        rms = [
            'size',
            'relativeTransform',
            'absoluteBoundingBox',
            'absoluteRenderBounds',
            'fillGeometry',
            'strokeGeometry',
            'blendMode',
            'scrollBehavior',
            'strokeAlign',
            'strokeWeight',
            'style',
            'cornerRadius',
            'characterStyleOverrides',
            'styleOverrideTable',
            'layoutAlign',
            'layoutGrow',
            'clipsContent',
            'background',
            'backgroundColor',
            'preserveRatio',
            'constraints',
            'layoutMode',
            'counterAxisSizingMode',
            'itemSpacing',
            'primaryAxisSizingMode',
            'counterAxisAlignItems',
            'primaryAxisAlignItems',
            'paddingLeft',
            'paddingRight',
            'paddingTop',
            'paddingBottom',
            'exportSettings',
        ]
        for k in [key for key in record.keys()] + rms:
            if k in record['data']:
                try:
                    del record['data'][k]
                except:
                    ...

        yield record
    except Exception as e:
        raise KeyError(f'{id}: {e}')


def absrel(a, b, k):
    try:
        return (getfrom(a, "absoluteBoundingBox", k, default=0) - getfrom(b, "absoluteBoundingBox", k, default=0))
    except:
        # the x, y, width, height can be null for BOOLEAN_OPERATION and other nodes.
        return None


def zip_box_shadow(node: dict):
    """
    extract box-shadow properties if present
    """
    if 'effects' not in node or node['effects'] is None or len(node['effects']) == 0:
        return None

    # filter non visible effects
    effects = [effect for effect in node['effects'] if effect.get('visible')]
    # filter non box-shadow effects
    effects = [effect for effect in effects if effect['type'] == 'DROP_SHADOW']

    if len(effects) == 0:
        return None
    else:
        # if more than one box-shadow, still, return the first one.
        return effects[0]


def zip_export_settings(node):
    """
    return the most format for export

    `[{'suffix': '', 'format': 'PNG', 'constraint': {'type': 'SCALE', 'value': 1.0}}]`

    -> `PNG`
    """

    if 'exportSettings' not in node:
        return None

    if len(node['exportSettings']) == 0:
        return None

    if len(node['exportSettings']) == 1:
        return node['exportSettings'][0]['format']

    # if there are more than one export settings, return the most common format.
    formats = [setting['format'] for setting in node['exportSettings']]
    return max(formats, key=formats.count)


def zip_background_image(node: dict):
    image_paints = paints(node.get('fills'), type='IMAGE')

    def imgref(imgpaint):
        return imgpaint.get('imageRef') or imgpaint.get('gifRef')

    if len(image_paints) == 0:
        return None

    if len(image_paints) == 1:
        return imgref(image_paints[0])

    # return the first opacity 1 image, if all images are opacity lower than 1, return the first image.
    for image in image_paints:
        if image.get('opacity', 1) == 1:
            return imgref(image)

    return imgref(image_paints[0])


def zip_color(node, p='fills'):
    if p not in node or node[p] is None or len(node[p]) == 0:
        return None

    # filter non visible fills, filter only solid fills
    solids = paints(node[p], type='SOLID')

    if len(solids) == 0:
        return None
    if len(solids) == 1:
        return solids[0]['color']
    else:
        return blend_figma_fills_best_shot(solids)


def zip_background_color(node, p='fills'):
    """
    return the best-shot background color if present
    """

    if 'backgroundColor' in node:
        return node['backgroundColor']

    return zip_color(node, p=p)


def paints(paints: list[dict], type=None):
    """
    filter out non visible paints
    """

    if paints is None:
        return []
    # visible = True
    visible = [paint for paint in paints if paint.get('visible', True)]

    # opacity > 0
    visible = [paint for paint in visible if paint.get('opacity', 1) > 0]

    if type is None:
        return visible

    # filter with type
    return [paint for paint in visible if paint['type'] == type]


def blend_figma_fills_best_shot(solids):
    """
    blends the figma fills in the best way
    """

    colors = [fill['color'] for fill in solids]
    return blend_colors_porter_duff(colors)


def blend_colors_porter_duff(colors):
    """
    takes a list of rgba colors wher r, g, b, a is 0 to 1 (not 0 to 255)
    """
    def porter_duff_over(c1, c2):
        a1, a2 = c1[3], c2[3]
        a_out = a1 + a2 * (1 - a1)

        if a_out == 0:
            return [0, 0, 0, 0]

        return [(c1[i] * a1 + c2[i] * a2 * (1 - a1)) / a_out for i in range(3)] + [a_out]

    try:
        result = [0, 0, 0, 0]
        for color in colors:
            result = porter_duff_over(result, color)
        return result
    except:
        return None


def hex8(rgba):
    """
    takes a list of rgba colors wher r, g, b, a is 0 to 1 (not 0 to 255)

    takes list or tuple or dict
    """
    if rgba is None:
        return None

    if isinstance(rgba, dict):
        rgba = [rgba['r'], rgba['g'], rgba['b'], rgba.get('a', 1)]

    return f'#{"".join([hex(int(c * 255))[2:].zfill(2) for c in rgba])}'
