import os
import hashlib
from datetime import datetime

def get_file_info(file_path: str) -> dict:
    """
    Return the file size and md5checksum value of the selected file with dictionary.

    Usage:
        from filetool import get_file_info
        info = get_file_info("bc_mmo_pwi-efd_l2_l-spec_20181109_r01-v00-00.cdf")
        info
    
    Parameters:
        filepath (str): file path
    
    Returns:
        dict: {"creation_time": creation time (ISO format), "size": file size (byte), "md5": MD5 (string)}
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get file size
    size = os.path.getsize(file_path)

    # Get file stamp
    file_stat = os.stat(file_path)
    file_stamp = file_stat.st_ctime
    creation time = datetime.fromtimestamp(file_stamp).isoformat() # ISO format


    # Get md5 chksum value for the input file
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    return {
        "creation time": creation time,
        "size": size,
        "md5": md5_hash.hexdigest()
    }

