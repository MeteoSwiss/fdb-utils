import os
from pathlib import Path

def is_directory_larger_than(directory: Path | str, size_limit_human_readable: str) -> bool:
    # Convert human-readable size to bytes
    size_limit_bytes = {
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }[size_limit_human_readable[-2:]] * float(size_limit_human_readable[:-2])

    # Get the size of the directory
    size_in_bytes = get_directory_size(directory)

    # Check if the directory size is larger than the limit
    return size_in_bytes > size_limit_bytes



def get_directory_size(directory: Path | str) -> int:
    total_size = 0
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_file():
                total_size += entry.stat().st_size
            elif entry.is_dir():
                total_size += get_directory_size(entry.path)
    return total_size
