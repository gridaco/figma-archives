import os
import glob
import click
import boto3
from pathlib import Path
from tqdm import tqdm
from botocore.exceptions import NoCredentialsError

s3 = boto3.client('s3')


@click.command()
@click.argument('local_folder', type=click.Path(exists=True, file_okay=False))
@click.argument('bucket', type=str)
@click.option('--pattern', default='*.json*', help='The pattern of files to match.')
def sync_files(local_folder, bucket, pattern):
    # Normalize local_folder to ensure it ends with '/'
    local_folder = os.path.join(local_folder, "")
    local_pattern = local_folder + '**/' + pattern
    # Generate a list of files to upload
    files = [f for f in glob.glob(
        local_pattern, recursive=True)]

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

    with tqdm(total=len(files)) as pbar:
        for filepath in files:
            with open(filepath, 'rb') as data:
                # Create the key by removing the local_folder prefix from the filepath
                key = os.path.relpath(filepath, local_folder)
                try:
                    if filepath.endswith('.json.gz'):
                        s3.upload_fileobj(data, bucket, key,
                                          ExtraArgs={'ContentType': 'application/json', 'ContentEncoding': 'gzip'})
                    elif filepath.endswith('.json'):
                        s3.upload_fileobj(data, bucket, key,
                                          ExtraArgs={'ContentType': 'application/json'})
                    else:
                        # skip
                        tqdm.write(
                            f'☐ Skipping - {filepath} is not a json or json.gz file')
                        continue
                    pbar.update()
                except FileNotFoundError:
                    tqdm.write(
                        f'☒ FileNotFoundError - {filepath} was not found')
                    continue
                tqdm.write(
                    f'☑ {filepath} ➡ s3://{bucket}/{key}')


if __name__ == "__main__":
    sync_files()
