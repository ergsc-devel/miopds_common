"""File information helpers (size, MD5 checksum, time stamp).
ファイル情報（サイズ、MD5 チェックサム、日時）を求める補助関数。

Usage / 使い方:
    from miopds_common import filetool

    filetool.get_file_info("data.cdf")  # {"creation_time", "size", "md5"}
    filetool.md5_of_file("data.cdf")
    filetool.md5_of_bytes(b"...")
"""

from .filetool import get_file_info, md5_of_bytes, md5_of_file

__all__ = ["get_file_info", "md5_of_bytes", "md5_of_file"]
