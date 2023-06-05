import os
import string
from concurrent.futures import ThreadPoolExecutor
from glob import glob

import shortuuid
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator

output_folder = "large-output-2023-2"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

cc_main_files = glob("CC-MAIN-*gz")

invalid_status_code = [401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 421, 422, 423, 424, 425, 426, 428, 429, 431, 451, 500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511]

def plain_text_percentage(content):
    total_chars = len(content)
    if total_chars == 0:
        return 0
    text_chars = sum(c in string.printable for c in content)
    return (text_chars / total_chars) * 100

def process_cc_main_file(cc_main_file):
    print("Processing file: " + cc_main_file)
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

                    content = record.raw_stream.read()

                    if len(content) > 1000:
                        soup = BeautifulSoup(content, 'html.parser' if 'text/html' in content_type else 'html5lib')
                        text_content = soup.get_text()
                        if plain_text_percentage(text_content) > 80:
                            continue
                    with open(file_path, 'wb') as out_file:
                        crawled_address = f"<!-- {url} -->\n".encode()
                        out_file.write(crawled_address)
                        out_file.write(content)

    os.remove(cc_main_file)
    print(f"Removed file: {cc_main_file}")

if __name__ == "__main__":
    with ThreadPoolExecutor() as executor:
        executor.map(process_cc_main_file, cc_main_files)

