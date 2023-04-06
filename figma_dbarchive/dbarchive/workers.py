import gc
import json
from queue import Queue, Empty
import sqlite3
import time
from tqdm import tqdm
from .node import process_node, roots_from_file
from .table import create_table, insert_node
from .lock import update_processed_files, processed_files



def create_connection(db_file):
    conn = sqlite3.connect(db_file)
    return conn

# Worker function for multithreading
def dbworker(queue: Queue, db: str, pbarpos: int):
    # Create a new SQLite database or open an existing one
    conn = create_connection(db)

    # Create the table in the database if it doesn't already exist
    create_table(conn)

    timeout = 60  # if there is no more items in the queue for 60 seconds after the last successful pop, exit.
    progress = tqdm(total=0, position=pbarpos, desc='📀', leave=True)
    while True:
        try:
            progress.total = progress.n + queue.qsize()
            payload, command = queue.get(timeout=timeout)
            progress.update(1)
            if command is None:
                break
            if command == 'PUT':
                insert_node(conn, **payload)
                # tqdm.write(f'☑ {payload["file_id"]}/{payload["node_id"]}')
        except Empty:
            # Exit the loop if the queue is empty for the specified timeout duration
            break

    conn.close()
    

def fileworker(queue: Queue, db: Queue, depth, threshold=4096, clean=False):
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
                        'data': strfy(processed.get('data')),
                        'children': strfy(processed.get('children')),
                        'fills': strfy(processed.get('fills')),
                        'effects': strfy(processed.get('effects')),
                        'constraints': strfy(processed.get('constraints')),
                        'strokes': strfy(processed.get('strokes')),
                        'export_settings': strfy(processed.get('export_settings')),
                    }
                    db.put((record, 'PUT'))
                    del processed
                    del record
            del root_nodes
            if clean:
              gc.collect()
            update_processed_files(1)
        except Exception as e:
            tqdm.write(f'Error processing {file_id}: {e}')
            update_processed_files(1)
            continue
        time.sleep(0.1)

def strfy(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return json.dumps(obj, indent=0, separators=(',', ':'))
    return str(obj)