import json
from pathlib import Path
from urllib.parse import urlparse
import click


@click.command()
@click.argument("progress", type=click.Path(exists=True))
@click.option("--overwrite", is_flag=True, type=click.BOOL, default=True)
def main(progress, overwrite):
    """
    Validates and removes invalid records from progress file.
    """

    # Load progress data
    with open(progress, 'r') as f:
        progress_data = json.load(f)

    # Transform progress data into an array of dictionaries
    progress_list = [{"link": k, "file": v}
                     for k, v in progress_data.items()]

    # Validate records in progress_list
    valid_progress_list = [
        record for record in progress_list if validate_record(record)]

    # Save valid progress data back to the progress file or to a new file
    if overwrite:
        with open(progress, 'w') as f:
            json.dump({item["link"]: prettyfy_file_url(item["file"])
                      for item in valid_progress_list}, f, indent=2)
    else:
        with open(Path(progress).with_suffix('.validated.json'), 'w') as f:
            json.dump({item["link"]: prettyfy_file_url(item["file"])
                      for item in valid_progress_list}, f, indent=2)


def prettyfy_file_url(url):
    """
    returns only useful part of the file url

    from: "https://www.figma.com/file/saSlOlI9ByxdR5ZhKho0es/coolicons-%7C-Free-Iconset-(Community)?t=1ciQyVhaH7kbu3ws-0"

    to: "https://www.figma.com/file/saSlOlI9ByxdR5ZhKho0es
    """
    parsed = urlparse(url)
    filekey = parsed.path.split('/')[2]
    return parsed.scheme + "://" + parsed.netloc + "/file/" + filekey


def validate_record(record):
    """
    Validate a record based on your validation criteria.

    Args:
        record (dict): A dictionary containing a record with "link" and "file".

    Returns:
        bool: True if the record is valid, False otherwise.
    """
    # Add your validation logic here

    file: str = record["file"]

    if file is None:
        return False

    if file == "":
        return False

    return file.startswith('https://www.figma.com/file/')


if __name__ == '__main__':
    main()
