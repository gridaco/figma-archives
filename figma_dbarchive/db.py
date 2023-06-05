import random
import threading
from pathlib import Path
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import time
import click
from tqdm import tqdm

from dbarchive.workers import dbworker, fileworker
from dbarchive.lock import get_processed_files

PBARPOS = 8


@click.command()
# command mode - 'sync' / 'populate' (populate mode is used when you want to process deeper in second entry, when first entry is processed with samples)
@click.argument("mode", type=click.STRING, default="sync")
@click.argument("src", type=click.Path(exists=True), required=True)
@click.option("--db", type=click.Path(file_okay=True, dir_okay=False), default="samples.db", help="Path to the SQLite database file")
@click.option("-c", "--concurrency", default=4, help="Number of threads to utilize")
@click.option("--depth", default=None, type=click.INT, help="Depth to process under each root node (defaults to None, which means no limit)")
@click.option("--max", default=None, type=click.INT, help="Max n of samples to process. defaults to None, which means no limit.")
@click.option("--shuffle", default=False, is_flag=True, help="Rather to shuffle order to process samples")
@click.option("--gc", default=False, is_flag=True, help="Rather to use GC after each process")
def main(mode, src, db, concurrency, depth, max, shuffle, gc):
    # if db's qsize is bigger than this, wait the file processing for the db thread to catch up.
    dbthreshold = 4096 * concurrency * \
        ((depth if depth is not None else 4) ** + 1)

    if concurrency < 1:
        raise ValueError("Concurrency must be greater than 0")

    if mode == "sync":
        ...
    elif mode == "populate":
        raise NotImplementedError("populate mode is not implemented yet")
        ...
    else:
        raise ValueError("mode must be 'sync' or 'flatten'")

    samples_path = Path(src)

    # Create a queue and populate it with file IDs and their respective paths
    file_queue = Queue()
    db_queue = Queue()

    dbthread = threading.Thread(
        target=dbworker, args=(db_queue, db, PBARPOS - 1))
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
    progress_bar = tqdm(total=total_files, desc="📂",
                        position=PBARPOS, leave=True)

    # fileworker(file_queue, db_queue, depth, dbthreshold, gc)
    # Process files using multiple threads
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        threads = []
        for _ in range(concurrency):
            # position = PBARPOS - (3 + _)
            thread = executor.submit(
                fileworker, file_queue, db_queue, depth, dbthreshold, gc)
            threads.append(thread)

        # Update progress bar as files are processed
        while True:
            processed_files = get_processed_files()
            if processed_files < total_files:
                progress_bar.update(processed_files - progress_bar.n)
                time.sleep(1)  # Add a small sleep to avoid busy-waiting
            else:
                break
        progress_bar.update(processed_files - progress_bar.n)

    # send the sentinel value to the db_queue
    db_queue.put((None, None))

    dbthread.join()


if __name__ == "__main__":
    main()
