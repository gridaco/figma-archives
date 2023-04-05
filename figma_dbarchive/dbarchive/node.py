
import json
from tqdm import tqdm
from .utils import getfrom


def roots_from_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
        roots = []
        for canvas in data["document"]["children"]:
            for root in canvas["children"]:
                roots.append((root, canvas['id']))

        return roots


def process_node(node, depth, canvas, parent=None, current_depth=0):
    """
    if depth is None, it means we want to process all nodes
    """
    # Process the node and return the organized object
    if depth is not None and current_depth > depth:
        return
    
    if 'children' in node:
        for child in node['children']:
            yield from process_node(node=child, depth=depth, parent=node, canvas=canvas, current_depth=current_depth+1)

    try:
      record = {}

      # switch-case types
      type = node['type']

      # geometry
      record = {
          **record,
          'x': rel(node, parent, 'x'),
          'x_abs': getfrom(node, "absoluteBoundingBox", "x", default=0),
          'y': rel(node, parent, 'y'),
          'y_abs': getfrom(node, "absoluteBoundingBox", "y", default=0),
          # if geometry=paths is not set while archiving, the "size" parameter can be empty. (we an use 'or' cuz, if, 0, the second one will also be 0.)
          'width': getfrom(node, "size", "x") or getfrom(node, "absoluteBoundingBox", "width"),
          'height': getfrom(node, "size", "y") or getfrom(node, "absoluteBoundingBox", "height"),
          # 
          'rotation': getfrom(node, 'rotation', default=0),
      }

      # general
      record = {
          **record,
          'node_id': node['id'],
          'parent_id': parent['id'] if parent else None,
          'type': type,
          'name': node['name'],
          'depth': current_depth,
          'opacity': node.get('opacity', 1),
          # 'color': node['fills'][0]['color'],
          # fills
          # strokes
          'canvas_id': canvas,
          'border_width': node.get('strokeWeight', 0),
          # 'border_color': ,
          'border_radius': node.get('cornerRadius', 0),
          # 'box_shadow_offset_x': node['effects'][0]['offset']['x'],
          # 'box_shadow_offset_y': node['effects'][0]['offset']['y'],
          # 'box_shadow_blur': node['effects'][0]['radius'],
          # 'box_shadow_spread': node['effects'][0]['spread'],
          # 'margin_top': ,
          # 'margin_right': ,
          # 'margin_left': ,
          # 'margin_bottom': ,
          # 'padding_top': ,
          # 'padding_left': ,
          # 'padding_right': ,
          # 'padding_bottom': ,        
      }    

      if type == "TEXT":
          _style = node.get('style')
          record = {
              **record,
              'text': node.get('characters', ''),
              'font_family': _style.get('fontFamily'),
              'font_weight': _style.get('fontWeight'),
              'font_size': _style.get('fontSize'),
              'text_align': _style.get('textAlignHorizontal'),
          }    

      # if the children is being handled, remove the 'children' from 'data' from record.
      if current_depth == depth:
          record['data'] = node
          # the last node in the depth
          ...
      else:
          # this node is parent to other nodes in the max depth
          if 'children' in node:
              record['data'] = {k: v for k, v in node.items() if k != 'children'}
              record['children'] = [child['id'] for child in node['children']]
              record['n_children'] = len(node['children'])
          else:
              record['data'] = node

      yield record
    except Exception as e:
        raise KeyError(f'{node["id"]}: {e}')


def rel(a, b, k):
    try:
      return (getfrom(a, "absoluteBoundingBox", k, default=0) - getfrom(b, "absoluteBoundingBox", k, default=0)) if parent else 0
    except:
      # the x, y, width, height can be null for BOOLEAN_OPERATION and other nodes.
      return None
