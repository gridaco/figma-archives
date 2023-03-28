import os
import re
import string
from glob import glob

import shortuuid
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator

output_folder = "large-output"

# Get a list of all files matching the "CC-MAIN-*" pattern in the current directory
cc_main_files = glob("CC-MAIN-*")

invalid_status_code = [401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 421, 422, 423, 424, 425, 426, 428, 429, 431, 451, 500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511]


def plain_text_percentage(content):
    total_chars = len(content)
    if total_chars == 0:
        return 0
    text_chars = sum(c in string.printable for c in content)
    return (text_chars / total_chars) * 100

# test_file = "CC-MAIN-20230320083513-20230320113513-00054.warc.gz"

# Iterate through all the matched files
for cc_main_file in cc_main_files:
    with open(cc_main_file, 'rb') as f:
        records = ArchiveIterator(f)
        for i, record in enumerate(records):
            if record.rec_type == 'response':
                url = record.rec_headers.get_header('WARC-Target-URI')
                content_type = record.http_headers.get_header('Content-Type')
                status_code = int(record.http_headers.get_statuscode())
                if status_code not in invalid_status_code and content_type and ('text/html' in content_type or 'text/css' in content_type or 'text/x-css' in content_type):
                    if 'map' in url:
                        continue
                    file_name = shortuuid.uuid()
                    file_ext = 'html' if 'text/html' in content_type else 'css'
                    file_path = os.path.join(output_folder, f"{file_name}.{file_ext}")
                    content = record.content_stream().read()
                    if len(content) > 10000:
                        # Use Beautiful Soup to extract the text content
                        soup = BeautifulSoup(content, 'html.parser' if 'text/html' in content_type else 'html5lib')
                        text_content = soup.get_text()
                        if plain_text_percentage(text_content) > 80:
                            continue
                        with open(file_path, 'wb') as out_file:
                            out_file.write(content)
