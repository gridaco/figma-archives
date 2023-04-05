from threading import Lock

processed_files = 0
processed_files_lock = Lock()

def update_processed_files(n=1):
    global processed_files
    with processed_files_lock:
        processed_files += n

def get_processed_files():
    global processed_files
    with processed_files_lock:
        return processed_files