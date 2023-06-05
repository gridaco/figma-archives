# this is a file syncer, which you can specify your own file pattern with wildcards to selectively upload files to s3
# this is useful when...
# - .json.gz types' content type and encoding must be specified
# - one-time-modifications are required.
# in most cases, you may want to use awscli's s3 sync instead - it's more efficient and optimized.
# this script does not have diff checking, so it will upload all files every time.

import os
import glob
import click
import boto3
import logging
import queue
import threading
from tqdm import tqdm
from botocore.exceptions import NoCredentialsError

s3 = boto3.client('s3')

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('failed-files.log')
handler.setLevel(logging.INFO)
logger.addHandler(handler)


DEFAULT_HEADERS = {
    'Cache-Control': 'public, max-age=2592000',
}


class UploadWorker(threading.Thread):
    def __init__(self, upload_queue, local_folder, bucket, pbar):
        threading.Thread.__init__(self)
        self.upload_queue = upload_queue
        self.local_folder = local_folder
        self.bucket = bucket
        self.pbar = pbar

    def run(self):
        while True:
            filepath = self.upload_queue.get()
            if filepath is None:
                break
            self.upload_file(filepath)
            self.upload_queue.task_done()

    def upload_file(self, filepath):
        with open(filepath, 'rb') as data:
            # Create the key by removing the local_folder prefix from the filepath
            key = os.path.relpath(filepath, self.local_folder)
            try:
                if filepath.endswith('.json.gz'):
                    s3.upload_fileobj(data, self.bucket, key,
                                      ExtraArgs={'ContentType': 'application/json', 'ContentEncoding': 'gzip', **DEFAULT_HEADERS})
                elif filepath.endswith('.json'):
                    s3.upload_fileobj(data, self.bucket, key,
                                      ExtraArgs={'ContentType': 'application/json', **DEFAULT_HEADERS})
                else:
                    # skip
                    self.pbar.update()
                    return
            except FileNotFoundError:
                logger.info(filepath)  # Log the failed file
            self.pbar.update()


@click.command()
@click.argument('local_folder', type=click.Path(exists=True, file_okay=False))
@click.argument('bucket', type=str)
@click.option('--pattern', default='*.json*', help='The pattern of files to match.')
@click.option('-c', '--concurrency', default=64, help='The number of worker threads to use.')
def sync_files(local_folder, bucket, pattern, concurrency):
    # Normalize local_folder to ensure it ends with '/'
    local_folder = os.path.join(local_folder, "")
    local_pattern = local_folder + '**/' + pattern
    # Generate a list of files to upload
    files = [f for f in glob.glob(local_pattern, recursive=True)]

    if len(files) == 0:
        click.echo(
            f'No files found matching pattern "{pattern}" - "{local_pattern}".')
        return

    click.echo(
        f'Found {len(files)} files to upload (matching pattern "{pattern}").')
    # ask if to continue
    if click.confirm('Do you want to continue?'):
        pass
    else:
        return

    # Check for AWS credentials before starting the process
    try:
        s3.list_buckets()
    except NoCredentialsError:
        click.echo("No AWS credentials found.")
        return

    upload_queue = queue.Queue()

    with tqdm(total=len(files)) as pbar:
        # Start worker threads
        workers = []
        for _ in range(concurrency):
            worker = UploadWorker(upload_queue, local_folder, bucket, pbar)
            worker.start()
            workers.append(worker)
        # Enqueue files to upload
        for filepath in files:
            upload_queue.put(filepath)
        # Block until all tasks are done
        upload_queue.join()
        # Stop worker threads
        for _ in range(concurrency):
            upload_queue.put(None)
        for worker in workers:
            worker.join()


if __name__ == "__main__":
    sync_files()
