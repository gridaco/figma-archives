import gc
import json
import random
import sqlite3
import threading
from threading import Lock
from pathlib import Path
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import time

import click
from tqdm import tqdm

PBARPOS = 8

processed_files = 0
processed_files_lock = Lock()


# Utility functions
def create_connection(db_file):
    conn = sqlite3.connect(db_file)
    return conn

def create_table(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS nodes (
        file_id TEXT,
        node_id TEXT,
        parent_id TEXT,
        type TEXT,
        name TEXT,
        data TEXT,
        depth INTEGER,
        x REAL,
        x_abs REAL,
        y REAL,
        y_abs REAL,
        width REAL,
        height REAL,
        rotation REAL,
        opacity REAL,
        color TEXT,
        canvas_id TEXT,
        text TEXT,
        font_family TEXT,
        font_weight TEXT,
        font_size REAL,
        text_align TEXT,
        border_width REAL,
        border_color TEXT,
        border_radius REAL,
        box_shadow_offset_x REAL,
        box_shadow_offset_y REAL,
        box_shadow_blur REAL,
        box_shadow_spread REAL,
        margin_top REAL,
        margin_right REAL,
        margin_left REAL,
        margin_bottom REAL,
        padding_top REAL,
        padding_left REAL,
        padding_right REAL,
        padding_bottom REAL,
        PRIMARY KEY (file_id, node_id)
    )''')

def insert_node(
        conn: sqlite3.Connection,
        **kwargs
    ):

    # Unpack the kwargs dictionary using tuple assignment
    (
        file_id, node_id, parent_id, _type, name,
        data, depth,
        x, x_abs, y, y_abs, width, height, rotation,
        opacity, color,
        canvas_id,
        text, font_family, font_weight, font_size, text_align,
        border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        margin_top, margin_right, margin_left, margin_bottom,
        padding_top, padding_left, padding_right, padding_bottom
    ) = (
        kwargs['file_id'], kwargs['node_id'], kwargs.get('parent_id'), kwargs['type'], kwargs['name'],
        kwargs.get('data'), kwargs.get('depth'),
        kwargs['x'], kwargs['x_abs'], kwargs['y'], kwargs['y_abs'], kwargs['width'], kwargs['height'], kwargs.get('rotation'),
        kwargs.get('opacity'), kwargs.get('color'),
        kwargs.get('canvas_id'),
        kwargs.get('text'), kwargs.get('font_family'), kwargs.get('font_weight'), kwargs.get('font_size'), kwargs.get('text_align'),
        kwargs.get('border_width'), kwargs.get('border_color'), kwargs.get('border_radius'),
        kwargs.get('box_shadow_offset_x'), kwargs.get('box_shadow_offset_y'), kwargs.get('box_shadow_blur'), kwargs.get('box_shadow_spread'),
        kwargs.get('margin_top'), kwargs.get('margin_right'), kwargs.get('margin_left'), kwargs.get('margin_bottom'),
        kwargs.get('padding_top'), kwargs.get('padding_left'), kwargs.get('padding_right'), kwargs.get('padding_bottom')
    )

    cursor = conn.cursor()

    if data is not None and type(data) is not str:
        data = json.dumps(data, indent=0, separators=(',', ':'))

    cursor.execute('''INSERT OR IGNORE INTO nodes (
        file_id, node_id, parent_id, type, name, data, depth,
        x, x_abs, y, y_abs, width, height,
        rotation, opacity, color, canvas_id, text,
        font_family, font_weight, font_size, text_align,
        border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        margin_top, margin_right, margin_left, margin_bottom,
        padding_top, padding_left, padding_right, padding_bottom
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        file_id, node_id, parent_id, _type, name, data, depth,
        px(x), px(x_abs), px(y), px(y_abs), px(width), px(height),
        deg(rotation), o(opacity), color, canvas_id, text,
        font_family, font_weight, font_size, text_align,
        px(border_width), border_color, px(border_radius),
        px(box_shadow_offset_x), px(box_shadow_offset_y), px(box_shadow_blur), px(box_shadow_spread),
        px(margin_top), px(margin_right), px(margin_left), px(margin_bottom),
        px(padding_top), px(padding_left), px(padding_right), px(padding_bottom)
    ))
    conn.commit()


def px(r):
    if r is None:
        return None
    return round(r, 2)

def o(r):
    if r is None:
        return None
    return round(r, 4)

def deg(r):
    if r is None:
        return None
    return round(r, 2)

def roots_from_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
        roots = []
        for canvas in data["document"]["children"]:
            for root in canvas["children"]:
                roots.append((root, canvas['id']))

        return roots


def getfrom(obj, *args, default=None):
    for key in args:
        try:
            obj = obj[key]
        except (KeyError, TypeError):
            return default
    return obj

def process_node(node, depth, canvas, parent=None, current_depth=0):
    # Process the node and return the organized object
    if current_depth > depth and depth is not None:
        return
    
    if 'children' in node:
        for child in node['children']:
            yield from process_node(node=child, depth=depth, parent=node, canvas=canvas, current_depth=current_depth+1)

    try:
      record = {}

      # switch-case types
      type = node['type']
      
      # general
      record = {
          **record,
          'node_id': node['id'],
          'parent_id': parent['id'] if parent else None,
          'type': type,
          'name': node['name'],
          'data': node,
          'depth': current_depth,
          'x': (getfrom(node, "absoluteBoundingBox", "x", default=0) - getfrom(parent, "absoluteBoundingBox", "x", default=0)) if parent else 0,
          'x_abs': getfrom(node, "absoluteBoundingBox", "x", default=0),
          'y': (getfrom(node, "absoluteBoundingBox", "y", default=0) - getfrom(parent, "absoluteBoundingBox", "y", default=0)) if parent else 0,
          'y_abs': getfrom(node, "absoluteBoundingBox", "y", default=0),
          'width': getfrom(node, "absoluteBoundingBox", "width"),
          'height': getfrom(node, "absoluteBoundingBox", "height"),
          'rotation': getfrom(node, 'rotation', 0),
          'opacity': node.get('opacity', 1),
          # 'color': node['fills'][0]['color'],
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


      yield record
    except Exception as e:
        tqdm.write(f'Error processing node {node["id"]}: {e}')
        raise e



def fileworker(queue: Queue, db: Queue, depth, threshold=4096, clean=False):
    global processed_files
    while True:
        while db.qsize() > threshold:
            time.sleep(1)
        try:
            file_id, file_path = queue.get_nowait()
        except Empty:
            tqdm.write(f'File worker exiting')
            break
        
        try:
            root_nodes = roots_from_file(file_path)
            # tqdm.write(f'☐ {file_id} ({len(root_nodes)} items)')
            for node, canvas in root_nodes:
                for processed in process_node(node=node, canvas=canvas, parent=None, depth=depth):
                    record = {
                        'file_id': file_id,
                        **processed,
                        # dump here, so fileworker thread, so db thraed won't be overloaded.
                        'data': json.dumps(processed['data']),
                    }
                    db.put((record, 'PUT'))
                    del processed
                    del record
            del root_nodes
            if clean:
              gc.collect()
            with processed_files_lock:
                processed_files += 1
        except Exception as e:
            tqdm.write(f'Error processing {file_id}: {e}')
            with processed_files_lock:
                processed_files += 1
            continue
        time.sleep(0.1)


# Worker function for multithreading
def dbworker(queue: Queue, db: str):
    # Create a new SQLite database or open an existing one
    conn = create_connection(db)

    # Create the table in the database if it doesn't already exist
    create_table(conn)

    timeout = 60  # if there is no more items in the queue for 60 seconds after the last successful pop, exit.
    progress = tqdm(total=0, position=PBARPOS - 1, desc='📀', leave=True)
    while True:
        try:
            progress.total = progress.n + queue.qsize()
            payload, command = queue.get(timeout=timeout)
            progress.update(1)
            if command is None:
                break
            if command == 'PUT':
                insert_node(conn, **payload)
                tqdm.write(f'☑ {payload["file_id"]}/{payload["node_id"]}')
        except Empty:
            # Exit the loop if the queue is empty for the specified timeout duration
            break

    conn.close()
    


@click.command()
@click.argument("samples", type=click.Path(exists=True), required=True)
@click.option("--db", type=click.Path(file_okay=True, dir_okay=False), default="samples.db", help="Path to the SQLite database file")
@click.option("-c", "--concurrency", default=4, help="Number of threads to utilize")
@click.option("--depth", default=0, help="Depth to process under each root node")
@click.option("--max", default=None, type=click.INT, help="Max n of samples to process. defaults to None, which means no limit.")
@click.option("--shuffle", default=False, is_flag=True, help="Rather to shuffle order to process samples")
@click.option("--gc", default=False, is_flag=True, help="Rather to use GC after each process")
def main(samples, db, concurrency, depth, max, shuffle, gc):
    dbthreshold = 4096 * concurrency # if db's qsize is bigger than this, wait the file processing for the db thread to catch up.
    
    if concurrency < 1:
        raise ValueError("Concurrency must be greater than 0")

    samples_path = Path(samples)

    # Create a queue and populate it with file IDs and their respective paths
    file_queue = Queue()
    db_queue = Queue()

    dbthread = threading.Thread(target=dbworker, args=(db_queue, db))
    dbthread.start()

    # seed the file queue
    files = [f for f in samples_path.glob("*/file.json")]
    if shuffle:
        random.shuffle(files)
    n = 0
    for file_path in files:
        if max and n >= max:
            break
        file_id = file_path.parent.name
        file_queue.put((file_id, file_path))
        n += 1

    tqdm.write(f'Found {file_queue.qsize()} samples to process')

    # Progress bar using tqdm
    total_files = file_queue.qsize()
    progress_bar = tqdm(total=total_files, desc="📂", position=PBARPOS, leave=True)

    # Process files using multiple threads
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        threads = []
        for _ in range(concurrency):
            # position = PBARPOS - (3 + _)
            thread = executor.submit(fileworker, file_queue, db_queue, depth, dbthreshold, gc)
            threads.append(thread)

        # Update progress bar as files are processed
        while processed_files < total_files:
            progress_bar.update(processed_files - progress_bar.n)
            time.sleep(1)  # Add a small sleep to avoid busy-waiting
        progress_bar.update(processed_files - progress_bar.n)

    # send the sentinel value to the db_queue
    db_queue.put((None, None))

    dbthread.join()


if __name__ == "__main__":
  main()

