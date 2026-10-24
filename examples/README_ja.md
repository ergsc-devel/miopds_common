# shell スクリプトとテンプレートの見本（examples）

[English](README.md)

`examples/` は、miopds_common を使って PSA/PDS4 アーカイブを作るための見本です。
shell スクリプト、Jinja2 テンプレート、設定ファイル（JSON）が入っています。
各機器のリポジトリ（例：`instrument_repo`）に `pds/` という名前でコピーし、機器に合わせて書き換えて使います。

この文書は、各スクリプトの引数、環境変数、出力を調べるための説明書です。
最初から順に動かす手順は、[../README_ja.md](../README_ja.md) の「クイックスタート」にあります。
ディレクトリ構成も、クイックスタートの構成（Bundle をリポジトリの外の `~/pds4/bc_mmo_pwi/` に置く）を前提にします。
コマンドの例は、機器のリポジトリの一番上で実行するものとします。

見本は、BepiColombo Mio PWI 向けの値（`bc_mmo_pwi` など）を既定値に持っています。
ほかの機器では、コピーした後に機器の値へ書き換えてください。

## 中身

```text
examples/
├── scripts/     # shell スクリプト
├── templates/   # Jinja2 テンプレート（*.xml.j2）
└── config/      # 設定ファイル（*.json）
```

| ファイル | 用途 |
|---|---|
| `scripts/make_pds_label_for_mmo_cdf_data.sh` | CDF ファイル1つから観測ラベル（`.lblx`）を作る |
| `scripts/create_psa_collection_jinja.sh` | データの Collection のラベルとインベントリを作り、検証する |
| `scripts/create_psa_document_jinja.sh` | Document のラベルと Document Collection を作り、検証する |
| `scripts/create_psa_bundle_jinja.sh` | Bundle のラベルを作り、Bundle 全体を検証する |
| `scripts/cron_mk_cdf_to_pds.sh` | 上の4つを順に呼び、入力が変わった製品だけを作り直す（cron での定期実行を想定） |
| `templates/mmo_cdf_label_template_multi_dataset.xml.j2` | 観測ラベルのテンプレート |
| `templates/collection_template.xml.j2` | データの Collection のラベルのテンプレート |
| `templates/document_template.xml.j2` | Document のラベルのテンプレート |
| `templates/document_collection_template.xml.j2` | Document Collection のラベルのテンプレート |
| `templates/bundle_template.xml.j2` | Bundle のラベルのテンプレート |
| `config/mission.json` | ミッションの設定（すべての Mio の機器で共通） |
| `config/instrument_pwi.json` | 機器の設定（PWI の記入例） |
| `config/dataset_pwi_efd.json` | データセットの設定（PWI-EFD の記入例。`REPLACE_` の値を書き換えてから使う） |
| `config/authors_pwi_efd.json` | 著者リストの記入例（PWI-EFD） |
| `config/authors_instrument_example.json` | 著者リストのひな形 |
| `config/README.md`、`config/README_ja.md` | 設定ファイルの項目と、ラベルのどこに入るかの説明（英語、日本語） |

設定ファイルの書き方は [config/README_ja.md](config/README_ja.md) を見てください。

## 準備

### miopds_common のインストール

shell スクリプトは、`python -m miopds_common サブコマンド` の形で miopds_common を呼び出します。
miopds_common は、専用の venv（例：`~/mio_pds_validate`）にインストールしておきます。
venv の作り方とインストールの手順は、[../README_ja.md](../README_ja.md) の「インストール」にあります。

### サーバーごとに使う Python を指定する

Python のコマンドの名前（`python3` か `python` か）と venv の場所は、サーバーごとに違います。
そのため、スクリプトは環境変数 `PYTHON` に指定された Python を使います（指定がなければ `python3`）。
各サーバーで、miopds_common をインストールした Python を、次のどれかの方法で指定してください。

| 実行のしかた | 指定の方法 |
|---|---|
| 手で実行する | venv を有効にする（`source ~/mio_pds_validate/bin/activate`）か、`export PYTHON=~/mio_pds_validate/bin/python` を実行する |
| 1回だけ指定する | `PYTHON=~/mio_pds_validate/bin/python ./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi` のように、コマンドの前に書く |
| cron で実行する | crontab の行に `PYTHON=$HOME/mio_pds_validate/bin/python` を書く。cron は venv を有効にせず、PATH も最小限なので、この指定が必ず必要 |
| 機器のリポジトリで固定する | コピーした shell の `PYTHON="${PYTHON:-python3}"` の `python3` を、そのサーバーの Python の絶対パスに書き換える |

crontab の行の例を示します（パスは例です。サーバーに合わせて書き換えてください）。

```bash
0 3 * * * PYTHON=$HOME/mio_pds_validate/bin/python $HOME/instrument_repo/pds/scripts/cron_mk_cdf_to_pds.sh $HOME/pds4/bc_mmo_pwi >> $HOME/pds_chk_log/cron.log 2>&1
```

指定した Python に miopds_common が入っているかは、次のコマンドで確かめられます。

```bash
"$PYTHON" -c 'import miopds_common; print(miopds_common.__file__)'
```

入っていない Python を指定すると、スクリプトは `ERROR: miopds_common is not installed for python3`（`python3` の部分は指定した Python）と表示して止まります。

### PDS Validate 4.2.0 のインストール

PDS Validate は、NASA PDS が配布している Java の検証ツールです。
配布物は [GitHub の Releases](https://github.com/NASA-PDS/validate/releases) にあり、使い方は[公式の文書](https://nasa-pds.github.io/validate/)にあります。
以下では、配布物 `validate-4.2.0-bin.tar.gz` を `~/Downloads/` にダウンロードした例を示します。

1. Java が入っているかを確かめます。

   ```bash
   java -version
   ```

2. 展開先のディレクトリを作ります（`mkdir -p` は、ディレクトリがすでにあれば何もしません）。

   ```bash
   mkdir -p ~/local/pds
   ```

3. 配布物を展開します（`-C` は展開先の指定です）。`~/local/pds/validate-4.2.0/` ができます。

   ```bash
   tar -xzf ~/Downloads/validate-4.2.0-bin.tar.gz -C ~/local/pds
   ```

   ZIP の配布物（`validate-4.2.0-bin.zip`）を使う場合は、次のコマンドで展開します。

   ```bash
   unzip ~/Downloads/validate-4.2.0-bin.zip -d ~/local/pds
   ```

4. 起動できるかを確かめます。

   ```bash
   ~/local/pds/validate-4.2.0/bin/validate --help
   ```

ほかの場所に展開した場合は、その場所を環境変数 `VALIDATE_BIN` に指定してください。
Java の必要な版は、配布物のリリースノートで確かめてください。

### XML Catalog

PSA と BepiColombo の辞書を解決する XML Catalog（`pds4-validate-catalog.xml`）を用意し、その絶対パスを環境変数 `VALIDATE_CATALOG` に指定することをすすめます。
ファイルが見つからないとき、スクリプトは警告を表示し、Catalog なしで検証を続けます。

### 今のスクリプトに必要な設定

今のスクリプトは、クイックスタートの構成では、次の環境変数を指定しないと動きません。
これは不具合で、[Issue #7](https://github.com/ergsc-devel/miopds_common/issues/7) で直す予定です。

| 環境変数 | 指定する値（例） | 使うスクリプト | 指定しないとどうなるか |
|---|---|---|---|
| `TIMELINE` | `~/pds_config/mission_timeline.json` | 観測ラベル | `TIMELINE: unbound variable` で止まる |
| `MISSION_TIMELINE_FILE` | `~/pds_config/mission_timeline.json` | Collection | `config/mission_timeline.json` がないので止まる |
| `ARCHIVE_ROOT` | `~/pds4` | Collection | 既定値がサーバー固有のパスなので、Collection のディレクトリが見つからず止まる |
| `VALIDATE_BIN` | `~/local/pds/validate-4.2.0/bin/validate` | Collection、Bundle | 既定値が `~/local/pds/validate/bin/validate` なので、検証の段階で止まる |

期間表（`mission_timeline.json`）の作り方は、[../README_ja.md](../README_ja.md) の「期間表を作る」にあります。

## スクリプトに共通の決まり

- テンプレートと設定ファイルは、スクリプトの場所からの相対パス（`../templates/`、`../config/`）で探します。
- 検証のレポートは、実行した場所からの相対パス（既定は `./pds_chk_log/`）に保存します。
- 観測ラベルのスクリプトを除き、作ったラベルを `python -m miopds_common validate` で検証します。
- どこかで失敗すると、その時点で止まります。
  ただし、PDS Validate が検証エラーのときに0以外の終了コードを返すかは、まだ確かめていません。
  検証の後は、レポートを読んでください（[../docs/usage_ja.md](../docs/usage_ja.md) の「既知の問題」）。

すべてのスクリプトで使える環境変数は、次のとおりです。

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `PYTHON` | miopds_common をインストールした Python | `python3` |
| `VALIDATE_ENABLED` | `0` にすると検証を省く | `1` |
| `VALIDATE_BIN` | PDS Validate の実行ファイル | Document：`$HOME/local/pds/validate-4.2.0/bin/validate`。Collection と Bundle：`$HOME/local/pds/validate/bin/validate` |
| `VALIDATE_CATALOG` | XML Catalog のパス（空にすると Catalog を使わない） | `pds4-validate-catalog.xml` |
| `REPORT_DIR` | 検証のレポートの保存先 | `./pds_chk_log` |
| `REPORT_TIMESTAMP` | レポートのファイル名に付ける日時 | 実行した日時 |

検証を省く例を示します。

```bash
VALIDATE_ENABLED=0 ./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

## 各スクリプト

Bundle のラベルは Collection のラベルを集めて作るので、スクリプトは次の順に実行します。

1. 観測ラベル（`make_pds_label_for_mmo_cdf_data.sh`）
2. データの Collection（`create_psa_collection_jinja.sh`）
3. Document（`create_psa_document_jinja.sh`。Document を入れるときだけ）
4. Bundle（`create_psa_bundle_jinja.sh`）

この4つを順にまとめて実行するのが `cron_mk_cdf_to_pds.sh` です。

### 観測ラベル：`make_pds_label_for_mmo_cdf_data.sh`

CDF ファイル1つから、観測ラベルを1つ作ります。このスクリプトは検証をしません。

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [OPTIONS...]
```

| 引数 | 意味 |
|---|---|
| `CDF_FILE` | CDF ファイル |
| `TEMPLATE_DIR` | テンプレートのディレクトリ |
| `TEMPLATE_NAME` | テンプレートの名前。`""` にすると `mmo_cdf_label_template_multi_dataset.xml.j2` |
| `OUTPUT_DIR` | 出力先のディレクトリ |
| `OPTIONS` | 5つ目以降の引数は、`python -m miopds_common cdf2pdslabel` のオプションとしてそのまま渡る |

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `TIMELINE` | 期間表のファイル（今は必須。上の「今のスクリプトに必要な設定」） | なし |
| `MISSION_CONFIG` | ミッションの設定ファイル | `config/mission.json` |
| `DATASET_CONFIG` | データセットの設定ファイル（機器と著者の設定は、この中に書いたパスから読む） | `config/dataset_pwi_efd.json` |

出力は `OUTPUT_DIR/CDF のファイル名.lblx` です（`.cdf` を `.lblx` に変えた名前）。
ミッションフェーズは、期間表の中で観測開始時刻が入る期間から決まります。
`--mission-phase-name` と `--mission-phase-id` をオプションに書くと、期間表より優先されます。
使えるオプションは `python -m miopds_common cdf2pdslabel --help` で確かめられます。

例を示します。

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates "" \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231
```

見本の `dataset_pwi_efd.json` は、`REPLACE_` の値を書き換えるまでエラーになります。

### Collection：`create_psa_collection_jinja.sh`

データの Collection のラベルとインベントリを作り、Collection のラベルを検証します。

```bash
./pds/scripts/create_psa_collection_jinja.sh [COLLECTION_NAME]
```

`COLLECTION_NAME` は Collection の名前です（既定は `data_calibrated_efd`）。英数字、`_`、`-` だけが使えます。

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `ARCHIVE_ROOT` | Bundle のディレクトリを置いた場所（今は必須） | サーバー固有のパス |
| `BUNDLE_NAME` | Bundle の名前 | `bc_mmo_pwi` |
| `COLLECTION_DIR` | Collection のディレクトリ | `$ARCHIVE_ROOT/$BUNDLE_NAME/$COLLECTION_NAME` |
| `LABEL_DIR` | 観測ラベルを探すディレクトリ（サブディレクトリの中も探す） | `$COLLECTION_DIR` |
| `COLLECTION_LID` | Collection の LID | `urn:jaxa:darts:$BUNDLE_NAME:$COLLECTION_NAME` |
| `OUTPUT_BASE` | 出力ファイルの名前（拡張子なし） | `$COLLECTION_NAME` |
| `TEMPLATE_FILE` | テンプレート | `templates/collection_template.xml.j2` |
| `MISSION_CONFIG` | ミッションの設定ファイル | `config/mission.json` |
| `DATASET_CONFIG` | データセットの設定ファイル | `config/dataset_pwi_efd.json` |
| `MISSION_TIMELINE_FILE` | 期間表のファイル（今は必須。JSON として読めるかを確かめるだけで、Collection には使わない） | `config/mission_timeline.json` |
| `PUBLICATION_YEAR` | 公開の年 | `2027` |
| `VERSION_ID` | Collection の版 | `1.0` |
| `VALIDATE_REPORT` | 検証で画面に出た内容の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt` |
| `SKIP_REPORT` | インベントリから外したラベルの一覧の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_skipped_missing_cdf.txt` |

出力は、`COLLECTION_DIR` の `OUTPUT_BASE.lblx`（ラベル）と `OUTPUT_BASE.csv`（インベントリ）です。
インベントリに入るのは、対応する CDF ファイルがある観測ラベルだけです。
CDF ファイルが見つからないラベルは、警告を表示し、その一覧を `SKIP_REPORT` に保存します。
この一覧は、アーカイブの中にラベルのないファイルを置かないよう、Collection のディレクトリには作りません。
前に作った Collection のラベルは `LABEL_DIR` の中にありますが、インベントリには入りません。

Collection の題名と説明は `DATASET_CONFIG` の `collection` から、Information Model の版は `MISSION_CONFIG` から読みます。

macOS では、このスクリプトは `find: -printf: unknown primary or operator` で止まります（Issue #7）。
macOS では、[../README_ja.md](../README_ja.md) のクイックスタートの B にある Python のコマンドを使ってください。

### Document：`create_psa_document_jinja.sh`

PDF から Document のラベルと Document Collection（ラベルとインベントリ）を作り、2つのラベルを検証します。

```bash
./pds/scripts/create_psa_document_jinja.sh [DOCUMENT_DIR]
```

`DOCUMENT_DIR` は PDF を置いたディレクトリです（既定は `bc_mmo_pwi/document`）。

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `PDF_FILE` | PDF の名前（`DOCUMENT_DIR` の中） | `bc_mmo_pwi_data_user_guide.pdf` |
| `DOCUMENT_LID` | Document の LID | `urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide` |
| `COLLECTION_LID` | Document Collection の LID | `urn:jaxa:darts:bc_mmo_pwi:document` |
| `VERSION_ID` | 版 | `1.0` |
| `TITLE` | Document の題名 | PWI のデータユーザーガイドの題名 |
| `DESCRIPTION` | Document の説明 | PWI のデータユーザーガイドの説明 |
| `PUBLICATION_YEAR` | 公開の年 | `2027` |
| `PUBLICATION_DATE` | 公開の日付 | `2027` |
| `MODIFICATION_DATE` | 変更の日付（`YYYY-MM-DD`） | 実行した日（UTC） |
| `DOCUMENT_MODIFICATION_DESCRIPTION` | Document のラベルの変更の説明 | 初版であることを示す文 |
| `COLLECTION_MODIFICATION_DESCRIPTION` | Document Collection の変更の説明 | 初版であることを示す文 |
| `DOCUMENT_OUTPUT` | Document のラベルの名前 | `bc_mmo_pwi_data_user_guide.lblx` |
| `COLLECTION_OUTPUT` | Document Collection のラベルの名前（`.lblx`） | `collection_bc_mmo_pwi_document.lblx` |
| `INVENTORY_OUTPUT` | インベントリの名前（`COLLECTION_OUTPUT` の `.lblx` を `.csv` に変えた名前にする） | `collection_bc_mmo_pwi_document.csv` |
| `DOCUMENT_TEMPLATE` | Document のテンプレート | `templates/document_template.xml.j2` |
| `COLLECTION_TEMPLATE` | Document Collection のテンプレート | `templates/document_collection_template.xml.j2` |
| `MISSION_CONFIG` | ミッションの設定ファイル | `config/mission.json` |
| `INSTRUMENT_CONFIG` | 機器の設定ファイル | `config/instrument_pwi.json` |
| `DOCUMENT_REPORT` | Document のラベルの検証の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_validate_report.txt` |
| `COLLECTION_REPORT` | Document Collection のラベルの検証の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_collection_validate_report.txt` |

出力は、`DOCUMENT_DIR` の Document のラベル、Document Collection のラベル、インベントリの3つです。
Document Collection のメンバーは、`DOCUMENT_DIR` の中にある Product_Document のラベル（`.lblx` と `.xml`）のうち、文書ファイルがあるものすべてです。
文書ファイルがないラベルは、警告を表示してメンバーから外します。
Document Collection の題名、説明、機器の名前は `INSTRUMENT_CONFIG` から、ミッションの名前と Information Model の版は `MISSION_CONFIG` から読みます。

例を示します。

```bash
./pds/scripts/create_psa_document_jinja.sh ~/pds4/bc_mmo_pwi/document
```

### Bundle：`create_psa_bundle_jinja.sh`

Bundle のディレクトリの下にある Collection のラベルを集めて Bundle のラベルを作り、Bundle 全体を検証します。

```bash
./pds/scripts/create_psa_bundle_jinja.sh [BUNDLE_DIR]
```

`BUNDLE_DIR` は Bundle のディレクトリです（既定は `bc_mmo_pwi`）。

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `BUNDLE_NAME` | Bundle の名前 | `BUNDLE_DIR` の最後の部分（例：`bc_mmo_pwi`） |
| `BUNDLE_LID` | Bundle の LID | `urn:jaxa:darts:$BUNDLE_NAME` |
| `BUNDLE_VID` | Bundle の版 | `1.0` |
| `PUBLICATION_YEAR` | 公開の年 | `2027` |
| `MODIFICATION_DATE` | 変更の日付（`YYYY-MM-DD`） | 実行した日（UTC） |
| `OUTPUT_FILE` | Bundle のラベルの名前 | `$BUNDLE_NAME.lblx` |
| `TEMPLATE_FILE` | テンプレート | `templates/bundle_template.xml.j2` |
| `MISSION_CONFIG` | ミッションの設定ファイル | `config/mission.json` |
| `INSTRUMENT_CONFIG` | 機器の設定ファイル | `config/instrument_pwi.json` |
| `BUNDLE_LABEL_EXTENSION` | 検証でラベルとみなす拡張子（空にすると PDS Validate の既定の `xml`） | `lblx` |
| `VALIDATE_REPORT` | PDS Validate 自身のレポート（`--report-file`）の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_report.txt` |
| `VALIDATE_LOG` | 検証で画面に出た内容の保存先 | `$REPORT_DIR/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_log.txt` |

出力は `BUNDLE_DIR/OUTPUT_FILE`（例：`~/pds4/bc_mmo_pwi/bc_mmo_pwi.lblx`）です。
Bundle のメンバーになるのは、`BUNDLE_DIR` の下にある Collection のラベルのうち、拡張子が `.lblx` のものだけです。
Bundle の題名と説明は `INSTRUMENT_CONFIG` の `bundle` から、Information Model の版は `MISSION_CONFIG` から読みます。
Bundle のラベルには、著者リストを書きません。
検証は、`--rule pds4.bundle` で Bundle 全体に対して行います。

例を示します。

```bash
./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

### まとめて実行・差分更新：`cron_mk_cdf_to_pds.sh`

観測ラベル、Collection、Document、Bundle を順に作り、入力が変わった製品だけを作り直します。
cron などで定期的に実行すると、CDF や設定の変更が、ラベル、Collection、Bundle に反映されます。

```bash
./pds/scripts/cron_mk_cdf_to_pds.sh [all] [BUNDLE_DIR]
```

| 引数 | 意味 |
|---|---|
| `all` | すべての製品を作り直す（`--all` でもよい） |
| `BUNDLE_DIR` | Bundle のディレクトリ（既定は `bc_mmo_pwi`） |

今のスクリプトは、次の構成を前提にしています。

```text
BUNDLE_DIR/data_calibrated_efd/science/**/*.cdf   データ（ラベルは CDF と同じディレクトリに作る）
BUNDLE_DIR/document/*.pdf                         文書（なければ Document の手順を飛ばす）
```

そのため、クイックスタートの構成（Collection の下にフェーズと年のディレクトリがある構成）では、`ERROR: directory not found: .../science` で止まります（Issue #7）。

製品は、出力がないとき、または次の入力のどれかが出力より新しいときに作り直します。

| 出力 | 入力 |
|---|---|
| 観測ラベル（CDF ごと） | その CDF、データセットの設定ファイル |
| Collection | `science/` の下のファイルとディレクトリ（追加と削除も含む） |
| Document と Document Collection | PDF（`PDF_FILE`） |
| Bundle | 各 Collection のラベル |
| すべての製品に共通 | `templates/`、`config/`、`scripts/`、miopds_common の Python のコード |

テンプレート、設定ファイル、shell のどれかを書き換えると、すべての製品を作り直します。
観測ラベルは CDF 1つごとに Python を起動するので、作り直す CDF が多いと時間がかかります。

機器に合わせて、スクリプトの中の次の2か所を書き換えます。

| 書き換える場所 | 内容 |
|---|---|
| `set_label_args` 関数 | CDF ごとに `cdf2pdslabel` へ渡す追加のオプション（ミッションフェーズ、internal reference など） |
| `make_data_collection` の行 | データの Collection ごとに、名前とデータセットの設定ファイルを1行ずつ書く。Collection を増やすときは行を足す |

| 環境変数 | 意味 | 既定値 |
|---|---|---|
| `BUNDLE_NAME` | Bundle の名前（ロックの名前と、Bundle のラベルの名前に使う） | `BUNDLE_DIR` の最後の部分 |
| `PDF_FILE` | Document の PDF の名前 | `bc_mmo_pwi_data_user_guide.pdf` |
| `DOCUMENT_OUTPUT` | Document のラベルの名前 | `bc_mmo_pwi_data_user_guide.lblx` |
| `COLLECTION_OUTPUT` | Document Collection のラベルの名前 | `collection_bc_mmo_pwi_document.lblx` |
| `OUTPUT_FILE` | Bundle のラベルの名前 | `BUNDLE_DIR` の最後の部分 + `.lblx` |
| `DATASET_CONFIG` | データの Collection のデータセットの設定ファイル | `config/dataset_pwi_efd.json` |
| `TEMPLATES_DIR` | テンプレートのディレクトリ | `templates/` |
| `CONFIG_DIR` | 設定ファイルのディレクトリ | `config/` |
| `LOCK_DIR` | ロックの場所 | `$TMPDIR/miopds_cron_mk_cdf_to_pds_${BUNDLE_NAME}.lock` |

実行の決まりは次のとおりです。

- 同じ Bundle に対しては、同時に1つしか実行できません（ロックを使います）。
  cron と手で実行するときで `TMPDIR` が違うときは、`LOCK_DIR` に固定の場所を指定してください。
  異常終了でロックが残ったときは、ほかに実行中でないことを確かめてから、ロックのディレクトリを `rmdir` で消してください。
- 1回の実行のレポートは、すべて同じ `REPORT_DIR` に、同じ日時（`REPORT_TIMESTAMP`）を付けて保存します。
- CDF がなくなったラベルは消さず、警告だけを表示します（Collection のインベントリからは外れます）。
- L2 CDF の作成と、データのディレクトリへのコピーは、このスクリプトより前に、各機器のパイプラインで行います。

## 関連する文書

| 文書 | 内容 |
|---|---|
| [../README_ja.md](../README_ja.md) | インストールと、最初から順に動かすクイックスタート |
| [../docs/usage_ja.md](../docs/usage_ja.md) | サブコマンドとオプション、Python からの使い方、`validate` サブコマンド、既知の問題 |
| [config/README_ja.md](config/README_ja.md) | 設定ファイルの項目と、ラベルのどこに入るか |
