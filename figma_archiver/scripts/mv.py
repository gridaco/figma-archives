import shutil
import click
import os
from pathlib import Path
from tqdm import tqdm
from queue import Queue
import threading


def buffered_move(src, dst, buffer_size=64*1024):
    with open(src, 'rb') as src_file, open(dst, 'wb') as dst_file:
        shutil.copyfileobj(src_file, dst_file, length=buffer_size)

    os.remove(src)


@click.command()
@click.argument('src', type=click.Path(exists=True, file_okay=False))
@click.argument('dst', type=click.Path(exists=True, file_okay=False))
@click.option('--threads', default=4, help='Number of threads to use.')
def move(src, dst, threads):
    src_path = Path(src)
    dst_path = Path(dst)
    file_queue = Queue()

    def index_files():
        items = [item for item in src_path.rglob('*') if item.name != '.DS_Store']
        sorted_items = sorted(items, key=lambda x: x.stat().st_size, reverse=True)
        for item in sorted_items:
            file_queue.put(item)

    def move_files():
        while not file_queue.empty():
            src_item = file_queue.get()
            dst_item = dst_path.joinpath(src_item.relative_to(src_path))
            try:
                if not dst_item.parent.exists():
                    os.makedirs(dst_item.parent)
                if src_item.is_file():
                    shutil.move(str(src_item), str(dst_item))
                elif src_item.is_dir():
                    os.rmdir(str(src_item))
                tqdm.write(f'Moved: {src_item} -> {dst_item}')
            except Exception as e:
                tqdm.write(f'Error moving {src_item}: {e}')
            file_queue.task_done()

    # Index files
    print('Indexing files...')
    index_files()

    # Move files using threads
    print(f'Moving files using {threads} threads...')
    with tqdm(total=file_queue.qsize()) as pbar:
        for _ in range(threads):
            t = threading.Thread(target=move_files)
            t.start()

        while not file_queue.empty():
            pbar.update()
            file_queue.join()
            pbar.close()

        for _ in range(threads):
            t.join()

    print('Move complete.')

if __name__ == '__main__':
    move()
