import os
import hashlib

def get_file_info(filepath: str) -> dict:
    """
    Return the file size and md5checksum value of the selected file with dictionary.

    Usage:
        from filetool import get_file_info
        info = get_file_info("bc_mmo_pwi-efd_l2_l-spec_20181109_r01-v00-00.cdf")
        info
    
    Parameters:
        filepath (str): file path
    
    Returns:
        dict: {"size": file size (byte), "md5": MD5 (string)}
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    # Get file size
    size = os.path.getsize(filepath)

    # Get md5 chksum value for the input file
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    return {
        "size": size,
        "md5": md5_hash.hexdigest()
    }

