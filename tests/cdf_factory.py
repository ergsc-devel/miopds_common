"""Create a small synthetic CDF file for tests (no real data needed).
テスト用の小さな合成 CDF ファイルを作る（実データは不要）。
"""

from pathlib import Path

import numpy as np
from cdflib.cdfwrite import CDF as CDFWriter

# Name with an observation date, as the label builder expects
# ラベル生成側が期待するとおり、観測日を含むファイル名にする
TEST_CDF_NAME = "bc_mmo_pwi-efd_l2_test_20270101_v01.cdf"
TEST_TIMES = [
    "2027-01-01T00:00:00.000Z",
    "2027-01-01T00:00:01.000Z",
    "2027-01-01T00:00:02.000Z",
]


def make_test_cdf(directory: Path) -> Path:
    """Write the synthetic CDF into directory and return its path.
    合成 CDF を directory に書き出し、そのパスを返す。

    Compress is 0 because cdftool supports uncompressed files only.
    cdftool は非圧縮のファイルにしか対応しないため、Compress は 0 にする。
    """
    path = Path(directory) / TEST_CDF_NAME
    writer = CDFWriter(str(path))
    writer.write_globalattrs({
        "PDS_LOGICAL_IDENTIFIER": {
            0: "urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd:"
            "bc_mmo_pwi-efd_l2_YYYYMMDD"
        },
        "PDS_VERSION_IDENTIFIER": {0: "1.0"},
        # "&" checks that XML escaping works / "&" で XML の置き換えを確かめる
        "TITLE": {0: "Synthetic PWI-EFD test product & check"},
        "Logical_source_description": {0: "Synthetic data for miopds_common tests"},
        "PDS_SCLK_START_COUNT": {0: "1/0000000001"},
        "PDS_SCLK_STOP_COUNT": {0: "1/0000000003"},
        "GENERATION_SOFTWARE": {0: "test-generator"},
        "SOFTWARE_VERSION": {0: "0.0.1"},
        "SOURCE_FILE": {0: "source_l1.cdf"},
    })
    base = {"Num_Elements": 1, "Rec_Vary": True, "Dim_Sizes": [], "Compress": 0}
    records = len(TEST_TIMES)

    # epoch: CDF_TIME_TT2000 (33)
    writer.write_var(
        {**base, "Variable": "epoch", "Data_Type": 33},
        {"CATDESC": "Epoch"},
        np.array([1, 2, 3], dtype=np.int64) * 10**9,
    )
    # strtime: CDF_CHAR (51), 24 characters per record / 1レコード24文字
    writer.write_var(
        {**base, "Variable": "strtime", "Data_Type": 51, "Num_Elements": 24},
        {"CATDESC": "Time string"},
        TEST_TIMES,
    )
    # freq: CDF_REAL4 (21), not record-varying / レコードによらない変数
    writer.write_var(
        {**base, "Variable": "freq", "Data_Type": 21,
         "Rec_Vary": False, "Dim_Sizes": [4]},
        {"UNITS": "Hz", "CATDESC": "Frequency"},
        np.array([1, 2, 3, 4], dtype=np.float32),
    )
    # E: CDF_REAL4 (21), shape (records, 4) with special values / 特殊値つき
    writer.write_var(
        {**base, "Variable": "E", "Data_Type": 21, "Dim_Sizes": [4]},
        {
            "UNITS": "mV/m",
            "CATDESC": "Electric field",
            "DEPEND_1": "freq",
            "FILLVAL": [-1e31, "CDF_REAL4"],
            "VALIDMIN": [-100.0, "CDF_REAL4"],
            "VALIDMAX": [100.0, "CDF_REAL4"],
        },
        np.arange(records * 4, dtype=np.float32).reshape(records, 4),
    )
    writer.close()
    return path
