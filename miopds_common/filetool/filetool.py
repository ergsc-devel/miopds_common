"""File information helpers (size, MD5 checksum, time stamp).
ファイル情報（サイズ、MD5 チェックサム、日時）を求める補助関数。

Used by the label builders in this package and by other pipelines.
このパッケージのラベル生成でも、他のパイプラインでも使う。
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path

# Read files in 1 MiB blocks so large CDF files do not fill memory.
# 大きな CDF ファイルでもメモリを使い切らないよう、1 MiB ずつ読む。
_MD5_CHUNK_SIZE = 1024 * 1024


def md5_of_file(path: str | os.PathLike) -> str:
    """Return the MD5 checksum of a file as a hexadecimal string.
    ファイルの MD5 チェックサムを16進数の文字列で返す。
    """
    digest = hashlib.md5()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(_MD5_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_of_bytes(data: bytes) -> str:
    """Return the MD5 checksum of in-memory data (e.g. a generated inventory CSV).
    メモリ上のデータ（生成したインベントリ CSV など）の MD5 チェックサムを返す。
    """
    return hashlib.md5(data).hexdigest()


def get_file_info(file_path: str | os.PathLike) -> dict:
    """
    Return the file size and md5checksum value of the selected file with dictionary.
    ファイルのサイズ、MD5 チェックサム、日時を辞書で返す。

    Usage:
        from miopds_common.filetool import get_file_info
        info = get_file_info("bc_mmo_pwi-efd_l2_l-spec_20181109_r01-v00-00.cdf")
        info

    Parameters:
        file_path (str or path-like): file path

    Returns:
        dict: {"creation_time": creation time (ISO format),
               "size": file size (byte),
               "md5": MD5 (string)}

    Note:
        creation_time comes from st_ctime in local time without a time zone.
        On Linux st_ctime is the time of the last metadata change, not creation.
        creation_time は st_ctime（ローカル時刻、タイムゾーンなし）から求める。
        Linux では st_ctime は作成時刻ではなく、属性を最後に変更した時刻。
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get file size / ファイルサイズ
    size = os.path.getsize(file_path)

    # Get file stamp / ファイルの日時
    file_stat = os.stat(file_path)
    file_stamp = file_stat.st_ctime
    creation_time = datetime.fromtimestamp(file_stamp).isoformat()  # ISO format

    return {
        "creation_time": creation_time,
        "size": size,
        "md5": md5_of_file(file_path),
    }
