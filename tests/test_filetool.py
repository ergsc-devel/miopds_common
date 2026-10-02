"""Tests for miopds_common.filetool.
miopds_common.filetool のテスト。
"""

import hashlib
import os
from datetime import datetime

import pytest

from miopds_common import filetool

# MD5 test vectors from RFC 1321 / RFC 1321 に載っている MD5 のテスト用の値
MD5_EMPTY = "d41d8cd98f00b204e9800998ecf8427e"
MD5_ABC = "900150983cd24fb0d6963f7d28e17f72"


def test_md5_of_bytes_known_values():
    # Known inputs give known checksums / 既知の入力から既知の値が出る
    assert filetool.md5_of_bytes(b"") == MD5_EMPTY
    assert filetool.md5_of_bytes(b"abc") == MD5_ABC


def test_md5_of_file_empty(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    assert filetool.md5_of_file(path) == MD5_EMPTY


def test_md5_of_file_larger_than_one_chunk(tmp_path):
    # 2.5 MiB, so the file is read in several blocks
    # 2.5 MiB にして、複数回に分けて読まれる場合も正しいことを確かめる
    data = bytes(range(256)) * (10 * 1024)
    path = tmp_path / "large.bin"
    path.write_bytes(data)
    assert filetool.md5_of_file(path) == hashlib.md5(data).hexdigest()


def test_get_file_info_is_unchanged(tmp_path):
    # Other pipelines may use this, so the result must stay the same
    # 他のパイプラインが使っている可能性があるため、返す値を変えないこと
    path = tmp_path / "abc.bin"
    path.write_bytes(b"abc")
    info = filetool.get_file_info(str(path))
    assert set(info) == {"creation_time", "size", "md5"}
    assert info["size"] == 3
    assert info["md5"] == MD5_ABC
    # st_ctime in local time, ISO format / st_ctime をローカル時刻の ISO 形式で
    expected = datetime.fromtimestamp(os.stat(path).st_ctime).isoformat()
    assert info["creation_time"] == expected


def test_get_file_info_accepts_path_objects(tmp_path):
    path = tmp_path / "abc.bin"
    path.write_bytes(b"abc")
    assert filetool.get_file_info(path)["md5"] == MD5_ABC


def test_get_file_info_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        filetool.get_file_info(tmp_path / "no_such.bin")
