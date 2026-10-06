# examples

miopds_common を使って PSA/PDS4 アーカイブを作るための**見本**です。
各機器のリポジトリ（例：mio_pwiam2p）に `examples/` をコピーし、機器に合わせて調整して使います。

> 現在の見本は BepiColombo Mio PWI 向けの値（`bc_mmo_pwi` など）を既定値として含んでいます。
> コピーした後、機器に合わせて書き換えてください。

## ディレクトリ構成

```text
examples/
├── scripts/     # shell スクリプト（python -m miopds_common の呼び出しと PDS Validate の実行）
├── templates/   # Jinja2 テンプレート（*.xml.j2）
└── config/      # 設定ファイル（authors_*.json）
```

| ファイル | 用途 |
|---|---|
| `scripts/make_pds_label_for_mmo_cdf_data.sh` | CDF ファイルから観測ラベル（`.lblx`）を生成 |
| `scripts/create_psa_collection_jinja.sh` | Collection ラベルとインベントリ CSV を生成して検証 |
| `scripts/create_psa_document_jinja.sh` | Product_Document と Document Collection を生成して検証 |
| `scripts/create_psa_bundle_jinja.sh` | Bundle ラベルを生成して Bundle 全体を検証 |
| `scripts/cron_mk_cdf_to_pds.sh` | 上の4本を呼び、古くなった製品だけを作り直す（親 shell。cron での定期実行を想定） |
| `templates/mmo_cdf_label_template_multi_dataset.xml.j2` | 観測ラベル用テンプレート |
| `templates/collection_template.xml.j2` | Collection ラベル用テンプレート |
| `templates/document_template.xml.j2` | Product_Document 用テンプレート |
| `templates/document_collection_template.xml.j2` | Document Collection 用テンプレート |
| `templates/bundle_template.xml.j2` | Bundle ラベル用テンプレート |
| `config/authors_instrument_example.json` | 著者リストのひな形 |
| `config/authors_pwi_efd.json` | 著者リストの記入例（PWI-EFD） |

## 準備

### 1. miopds_common のインストール

shell スクリプトは、`python -m miopds_common <サブコマンド>` の形で miopds_common（Python）を呼び出します。
まず、miopds_common 専用の venv（例：`~/mio_pds_validate`）を作り、そこにインストールします。
venv を作る `python3` は 3.11 以上である必要があります（`python3 --version` で確認）。

```bash
python3 -m venv ~/mio_pds_validate        # 専用の venv を作る（最初の1回だけ）
source ~/mio_pds_validate/bin/activate    # venv を有効化
pip install /path/to/miopds_common        # 開発中は pip install -e で編集を即時反映
```

#### サーバーごとに使う Python を指定する

Python のコマンド名（`python3` か `python` か）や venv の場所は、サーバーごとに違います。
スクリプトは推測せず、**環境変数 `PYTHON` に指定された Python** を使います（未指定なら `python3`）。
各サーバーで、miopds_common をインストールした Python を、次のどれかの方法で指定してください。

| 実行のしかた | 指定の方法 |
|---|---|
| 手で実行する | venv を有効にする（`source ~/mio_pds_validate/bin/activate`）。または `export PYTHON=~/mio_pds_validate/bin/python` |
| 1回だけ指定する | `PYTHON=~/mio_pds_validate/bin/python ./examples/scripts/cron_mk_cdf_to_pds.sh` |
| cron で実行する | crontab の行で `PYTHON=$HOME/mio_pds_validate/bin/python` を指定する（**必須**。cron は venv を有効にせず、PATH も最小限） |
| 各機器の repo で固定する | コピーした shell の `PYTHON="${PYTHON:-python3}"` の `python3` を、そのサーバーの Python の絶対パスに書き換える |

crontab の例（パスはサーバーに合わせて書き換える）：

```bash
0 3 * * * PYTHON=$HOME/mio_pds_validate/bin/python <repo>/examples/scripts/cron_mk_cdf_to_pds.sh <bundle_dir> >> <log_file> 2>&1
```

指定した Python に miopds_common が入っているかは、次のコマンドで確認できます。

```bash
"$PYTHON" -c 'import miopds_common; print(miopds_common.__file__)'
```

入っていない Python を指定すると、スクリプトは
`ERROR: miopds_common is not installed for <指定した Python>` で停止します。

#### サブコマンドとコマンドの対応

| サブコマンド（shell で使う形） | 同じ処理のコマンド | 処理 | Python の関数 |
|---|---|---|---|
| `python -m miopds_common cdf2pdslabel` | `miopds-label` | CDF → 観測ラベル | `_cli.label_main` |
| `python -m miopds_common labels2collection` | `miopds-collection` | ラベル群 → Collection | `_cli.collection_main` |
| `python -m miopds_common pdf2pdslabel` | `miopds-document` | PDF → Document のラベル | `_cli.document_main` |
| `python -m miopds_common pdf2document` | `miopds-document-set` | PDF → Document のラベル＋Document Collection | `_cli.document_set_main` |
| `python -m miopds_common collections2bundle` | `miopds-bundle` | Collection 群 → Bundle | `_cli.bundle_main` |
| `python -m miopds_common validate` | `miopds-validate` | PDS Validate の実行 | `_cli.validate_main` |

一覧は `python -m miopds_common --help`、各サブコマンドのオプションは
`python -m miopds_common <サブコマンド> --help` で確認できます。

### 2. PDS Validate 4.2.0 のインストール

PDS Validate は NASA PDS が提供する Java 製の検証ツールです。

- Releases: https://github.com/NASA-PDS/validate/releases
- 公式ドキュメント: https://nasa-pds.github.io/validate/

1. Java を確認します。

   ```bash
   java -version
   ```

2. Validate 4.2.0 の配布物（tar.gz または ZIP）を `$HOME/local/pds` へ展開します。

   ```bash
   mkdir -p "$HOME/local/pds"   # 展開先を作る（すでにあれば何もしない）
   cd "$HOME/local/pds"
   tar -xzf /path/to/validate-4.2.0.tar.gz
   # ZIP の場合
   unzip /path/to/validate-4.2.0.zip
   ```

3. 実行権限と起動を確認します。

   ```bash
   chmod +x "$HOME/local/pds/validate-4.2.0/bin/validate"
   "$HOME/local/pds/validate-4.2.0/bin/validate" --help
   ```

展開先が異なる場合は、実際のパスを環境変数 `VALIDATE_BIN` に指定してください。
Java の要件は、Validate 4.2.0 配布物のリリースノートを優先してください。

### 3. XML Catalog

PSA/BepiColombo の辞書を解決する `pds4-validate-catalog.xml` を用意し、
環境変数 `VALIDATE_CATALOG` に**絶対パス**で指定することを推奨します。
見つからない場合、スクリプトは警告を出して `--catalog` なしで検証を続けます。

## 実行の順番

Bundle は Collection ラベルを集めて作るため、次の順番で実行します。

1. 観測ラベル（label）
2. Collection（collection）
3. Document（document）
4. Bundle（bundle）

この順番で4本をまとめて実行するのが `cron_mk_cdf_to_pds.sh` です。

### まとめて実行・差分更新：`cron_mk_cdf_to_pds.sh`

```bash
./examples/scripts/cron_mk_cdf_to_pds.sh [all] [BUNDLE_DIR]
```

対象のファイルを巡回し、**古くなったものだけ**を作り直します（make と同じ考え方）。
定期的に実行（cron など）しておけば、CDF や設定の更新がラベル、Collection、Bundle に反映されます。

- 既定値：`BUNDLE_DIR=bc_mmo_pwi`。`all` を付けると、すべて作り直します。
- 想定するディレクトリ構成（`science/` の下は年ごとのサブディレクトリでもよい）：

  ```text
  BUNDLE_DIR/<collection>/science/**/*.cdf   データ（ラベルは CDF の隣に作る）
  BUNDLE_DIR/document/*.pdf                  文書（なければ手順3を飛ばす）
  ```

- 作り直す条件：出力がない、または次のどれかが出力より新しいとき。

  | 出力 | 入力 |
  |---|---|
  | 観測ラベル（CDF ごと） | その CDF、dataset の設定ファイル |
  | Collection | `science/` 以下のファイルとフォルダ（追加・削除も含む） |
  | Document と Document Collection | PDF（`PDF_FILE`） |
  | Bundle | 各 Collection のラベル |
  | （すべて共通） | `templates/`、`config/`、`scripts/`、miopds_common の Python コード |

  テンプレートや設定ファイル、shell を編集すると、すべての製品が作り直されます。
- CDF ごとに追加のオプション（ミッションフェーズ、internal reference など）を渡すときは、
  `cron_mk_cdf_to_pds.sh` の `set_label_args` 関数を編集します。
- データの Collection は、`cron_mk_cdf_to_pds.sh` の中に「名前と dataset の設定ファイル」の組で1行ずつ書きます。
  Collection を増やすときは、`make_data_collection ...` の行を追加してください。
- CDF がなくなったラベルは**削除せず**、警告だけを表示します（Collection からは除外されます）。
- 同じ Bundle に対しては同時に1つしか実行できません（ロック：`$TMPDIR/miopds_cron_mk_cdf_to_pds_<Bundle名>.lock`）。
  cron と手動の実行で `TMPDIR` が異なる場合は、`LOCK_DIR` で固定の場所を指定してください。
  異常終了などでロックが残った場合は、他に実行中でないことを確かめてから `rmdir` で削除してください。
- 今回の実行のレポートは、すべて同じ `REPORT_DIR` に、同じ日時（`REPORT_TIMESTAMP`）を付けて保存します。
- どこかの手順が失敗すると、その時点で止まります（後の手順は実行しません）。
- L2 CDF の作成と、`science/` へのコピーは、各機器のパイプラインで `cron_mk_cdf_to_pds.sh` より前に行います。

> **注意**：観測ラベルは CDF 1つごとに Python を起動するので、作り直す CDF が多いと時間がかかります。

## 各スクリプト

### 観測ラベル：`make_pds_label_for_mmo_cdf_data.sh`

```bash
./examples/scripts/make_pds_label_for_mmo_cdf_data.sh \
  CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [cdf2pdslabel のオプション...]
```

- 設定ファイルは環境変数 `MISSION_CONFIG`（既定：`config/mission.json`）と
  `DATASET_CONFIG`（既定：`config/dataset_pwi_efd.json`）で指定します。
  機器・著者の情報は、`dataset_*.json` から参照されるファイルから読み込まれます。
- 第5引数以降は `python -m miopds_common cdf2pdslabel` にそのまま渡され、上の既定値より優先されます。
- `TEMPLATE_NAME` に `""` を渡すと、`mmo_cdf_label_template_multi_dataset.xml.j2` を使います。
- 出力：`OUTPUT_DIR/<CDF ファイル名>.lblx`
- このスクリプトは PDS Validate を実行しません。

例：

```bash
./examples/scripts/make_pds_label_for_mmo_cdf_data.sh \
  bc_mmo_pwi-efd_l2_l-spec_20181109_r01-v00-00.cdf \
  examples/templates mmo_cdf_label_template_multi_dataset.xml.j2 out/ \
  --mission-phase-name Cruise --mission-phase-id cruise
```

ミッションフェーズは、既定では `mission.json` の値（Mercury Science Phase / `msp`）になります。
他のフェーズのデータでは、`--mission-phase-name` と `--mission-phase-id` を組で指定するか、
`--timeline` で期間表を指定してください（詳しくは `config/README.md`）。

見本の `dataset_pwi_efd.json` は Collection の文が `REPLACE_...` のままなので、
書き換えるまでは観測ラベルの生成もエラーになります（`config/README.md` を参照）。

オプションの一覧は `python -m miopds_common cdf2pdslabel --help` で確認できます。

### Collection：`create_psa_collection_jinja.sh`

```bash
./examples/scripts/create_psa_collection_jinja.sh [COLLECTION_NAME] [COLLECTION_DIR]
```

- 既定値：`COLLECTION_NAME=data_calibrated_efd`、`COLLECTION_DIR=bc_mmo_pwi/<COLLECTION_NAME>`
- 生成の後、Collection ラベルを `python -m miopds_common validate` で検証し、レポートを `VALIDATE_REPORT` に保存します。
- `LABEL_DIR`（既定：`<COLLECTION_DIR>/science`）以下の `.lblx` を探し、参照している CDF が揃っているラベルだけをインベントリに入れます。
- 出力：`<COLLECTION_DIR>/<OUTPUT_BASE>.lblx`（ラベル）、`.csv`（インベントリ）
- CDF が見つからず除外したラベルは、警告として表示し、一覧を `SKIP_REPORT`
  （既定：`<REPORT_DIR>/<日時>_<OUTPUT_BASE>_skipped_missing_cdf.txt`）に保存します。
  アーカイブの中にラベルのないファイルを置かないよう、Collection のディレクトリには作りません。

- Collection の title、description、collection_type は `DATASET_CONFIG`（`dataset_*.json` の `collection`）から、
  Information Model のバージョンは `MISSION_CONFIG`（`mission.json`）から読み込みます。
  見本の `dataset_pwi_efd.json` の `REPLACE_...` は、使う前に必ず書き換えてください（残っているとエラーになります）。

主な環境変数：`BUNDLE_NAME`、`LABEL_DIR`、`COLLECTION_LID`、`OUTPUT_BASE`、`TEMPLATE_FILE`、
`MISSION_CONFIG`（既定：`config/mission.json`）、`DATASET_CONFIG`（既定：`config/dataset_pwi_efd.json`）、
`PUBLICATION_YEAR`（既定：`2027`）、`VERSION_ID`（既定：`1.0`）、`SKIP_REPORT`

### Document：`create_psa_document_jinja.sh`

```bash
./examples/scripts/create_psa_document_jinja.sh [DOCUMENT_DIR]
```

- 既定値：`DOCUMENT_DIR=bc_mmo_pwi/document`
- `DOCUMENT_DIR` に PDF（既定：`bc_mmo_pwi_data_user_guide.pdf`）が必要です。
- 出力：Product_Document のラベル（`.lblx`）、Document Collection のラベル（`.lblx`）、インベントリ CSV
- Product_Document と Collection ラベルを個別に検証し、レポートを `DOCUMENT_REPORT` と `COLLECTION_REPORT` に保存します。
- Document Collection の title と description、機器名は `INSTRUMENT_CONFIG`（`instrument_*.json`）から、
  ミッション名と Information Model のバージョンは `MISSION_CONFIG`（`mission.json`）から読み込みます。
- Document Collection のメンバーは、`DOCUMENT_DIR` 以下の Product_Document ラベル（`.lblx` と `.xml`）すべてです
  （参照している文書ファイルがないラベルは、警告を出して除外します）。

主な環境変数：`DOCUMENT_LID`、`COLLECTION_LID`、`VERSION_ID`、`TITLE`、`DESCRIPTION`、
`PUBLICATION_YEAR`、`PUBLICATION_DATE`、`MODIFICATION_DATE`、`PDF_FILE`、
`DOCUMENT_MODIFICATION_DESCRIPTION`、`COLLECTION_MODIFICATION_DESCRIPTION`、
`DOCUMENT_OUTPUT`、`COLLECTION_OUTPUT`（`.lblx`）、`INVENTORY_OUTPUT`（`COLLECTION_OUTPUT` の `.lblx` を `.csv` にした名前）、
`DOCUMENT_TEMPLATE`、`COLLECTION_TEMPLATE`、
`MISSION_CONFIG`（既定：`config/mission.json`）、`INSTRUMENT_CONFIG`（既定：`config/instrument_pwi.json`）

### Bundle：`create_psa_bundle_jinja.sh`

```bash
./examples/scripts/create_psa_bundle_jinja.sh [BUNDLE_DIR]
```

- 既定値：`BUNDLE_DIR=bc_mmo_pwi`
- `BUNDLE_DIR` 以下の Collection ラベル（`*.lblx`）を集めて Bundle ラベルを作ります。`.xml` のラベルは使いません。
- Bundle の title と description は `INSTRUMENT_CONFIG`（`instrument_*.json` の `bundle`）から、
  Information Model のバージョンは `MISSION_CONFIG`（`mission.json`）から読み込みます。
- Bundle ラベルには著者リストを出力しません。
- 出力：`<BUNDLE_DIR>/<BUNDLE_NAME>.lblx`（例：`bc_mmo_pwi/bc_mmo_pwi.lblx`）
- `python -m miopds_common validate --rule pds4.bundle --label-extension lblx` で Bundle 全体を検証します。
  Validate 自身のレポート（`--report-file`）を `VALIDATE_REPORT` に、画面に出た内容を `VALIDATE_LOG` に保存します。

主な環境変数：`BUNDLE_NAME`、`BUNDLE_LID`、`BUNDLE_VID`、`PUBLICATION_YEAR`、`MODIFICATION_DATE`、
`OUTPUT_FILE`、`TEMPLATE_FILE`、`BUNDLE_LABEL_EXTENSION`（既定：`lblx`。空にすると Validate の既定の `xml`）、
`VALIDATE_REPORT`、`VALIDATE_LOG`、
`MISSION_CONFIG`（既定：`config/mission.json`）、`INSTRUMENT_CONFIG`（既定：`config/instrument_pwi.json`）

## 共通の環境変数

| 変数 | 意味 | 既定値 |
|---|---|---|
| `VALIDATE_ENABLED` | `0` にすると検証を省略 | `1` |
| `VALIDATE_BIN` | PDS Validate の実行ファイル | `$HOME/local/pds/validate-4.2.0/bin/validate` |
| `VALIDATE_CATALOG` | XML Catalog のパス | `pds4-validate-catalog.xml` |
| `REPORT_DIR` | 検証レポートの保存先（実行した場所からの相対パス） | `./pds_chk_log` |
| `REPORT_TIMESTAMP` | レポートのファイル名に付ける日時 | 実行した日時 |
| `PYTHON` | miopds_common をインストールした Python（**サーバーごとに指定**。上の「サーバーごとに使う Python を指定する」） | `python3` |

検証を省略する例：

```bash
VALIDATE_ENABLED=0 ./examples/scripts/create_psa_bundle_jinja.sh bc_mmo_pwi
```

## PDS Validate の実行（validate サブコマンド）

PDS Validate を実行し、出力を画面に表示しながらレポートファイルに保存します。
各スクリプトの検証はこれで行います。単独で、生成済みのラベルを検証し直すこともできます。

```bash
python -m miopds_common validate TARGET --report SCREEN_LOG [--report-file VALIDATE_REPORT] \
  [--validate-bin PATH] [--catalog CATALOG] [--rule pds4.bundle] [--label-extension lblx]
```

- `--report` には画面に出た内容を保存します。`--report-file` は Validate 自身のレポートで、
  Validate にそのまま渡します。2つに同じファイルは指定できません。
- `--catalog` のファイルがない場合は、警告を出して `--catalog` なしで続けます（空文字ならカタログなし）。
- 終了コードは Validate の終了コードをそのまま返します（0 以外ならスクリプトも止まります）。

## 既知の問題（今後の確認事項）

- PDS Validate が、検証エラーを見つけたときに 0 以外の終了コードを返すかは未確認です。
  0 を返す場合、エラーがあってもスクリプトは止まりません。レポートの内容を必ず確認してください。
- 観測ラベルの数値型は、CDF のバイト順に関係なく `MSB` になります（リトルエンディアンの CDF では誤り。修正は保留中）。
