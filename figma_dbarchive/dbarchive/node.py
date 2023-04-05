
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
          'x_abs': getfrom(node, "absoluteBoundingBox", "x", default=0),
          'y_abs': getfrom(node, "absoluteBoundingBox", "y", default=0),
          'rotation': getfrom(node, 'rotation', default=0),
      }
      if 'relativeTransform' in node:
          # size and relativeTransform is only present if geometry=paths is passed
          record = {
            **record,
            # https://github.com/gridaco/design-sdk/blob/main/figma-remote/lib/blenders/general.blend.ts
            'x': getfrom(node, "relativeTransform", 0, 2, default=0) if parent else 0,
            'y': getfrom(node, "relativeTransform", 1, 2, default=0) if parent else 0,
            'width': getfrom(node, "size", "x"),
            'height': getfrom(node, "size", "y"),
            # 
          }
      else:
          record = {
              **record,
              'x': absrel(node, parent, 'x') if parent else 0,
              'y': absrel(node, parent, 'y') if parent else 0,
              'width': getfrom(node, "absoluteBoundingBox", "width"),
              'height': getfrom(node, "absoluteBoundingBox", "height"),
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

      # finally, safely remove all keys from record, from record['data'] to reduce the size of the record.
      for k in [key for key in record.keys()]:
          if k in record['data']:
              try: del record['data'][k] 
              except: ...

      yield record
    except Exception as e:
        raise KeyError(f'{node["id"]}: {e}')


def absrel(a, b, k):
    try:
      return (getfrom(a, "absoluteBoundingBox", k, default=0) - getfrom(b, "absoluteBoundingBox", k, default=0))
    except:
      # the x, y, width, height can be null for BOOLEAN_OPERATION and other nodes.
      return None
