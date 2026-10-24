# miopds_common

[English](README.md)

## 概要

miopds_common は、BepiColombo/Mio（MMO）の観測データ（CDF）から PSA/PDS4 のアーカイブを作る Python パッケージです。
CDF ファイル1つごとの観測ラベル（`.lblx`）、Collection のラベルとインベントリ、Document のラベル、Bundle のラベルを作り、NASA PDS Validate で検証します。
Mio の各機器でアーカイブを担当する人が使うことを想定しています。

リポジトリは2つの部分に分かれています。
`miopds_common/` は、pip でインストールする Python パッケージです。
`examples/` には、shell スクリプト、Jinja2 テンプレート、設定ファイル（JSON）の見本があります。
`examples/` は pip ではインストールされないので、各機器のリポジトリにコピーして使います。

## インストール

miopds_common は、専用の venv（Python の仮想環境）にインストールします。
venv を分けておくと、ほかの作業で入れたパッケージと、miopds_common が使う cdflib、Jinja2、numpy の版がぶつかりません。

### 1. Python の版を確かめる

miopds_common には Python 3.11 以上が必要です。

```bash
python3 --version
```

`Python 3.11` 以上が表示されれば、そのまま使えます。
それより古い場合は、3.11 以上の Python（miniforge など）を入れるか、手順3の uv を使ってください。
uv は、指定した版の Python が見つからないとき、その版をダウンロードして venv を作ります。

### 2. ソースを取得する

ここでは、ホームディレクトリ（`~`）の下にソースを置く例を示します。

```bash
cd ~
```

```bash
git clone https://github.com/ergsc-devel/miopds_common.git
```

`~/miopds_common` ができます。

### 3. venv を作ってインストールする

venv の作り方は2通りあり、どちらか一方を使います。
以下では、venv の場所を `~/mio_pds_validate` とします（`examples/README.md` と同じ名前です）。

Python 標準の venv を使う場合は、次の3つを順に実行します。

```bash
python3 -m venv ~/mio_pds_validate
```

```bash
source ~/mio_pds_validate/bin/activate
```

```bash
pip install ~/miopds_common
```

uv を使う場合は、次の3つを順に実行します。
uv で作った venv には pip がないので、`uv pip install` の `--python` に venv の Python を指定します。

```bash
uv venv --python 3.13 ~/mio_pds_validate
```

```bash
source ~/mio_pds_validate/bin/activate
```

```bash
uv pip install --python ~/mio_pds_validate/bin/python ~/miopds_common
```

`source ~/mio_pds_validate/bin/activate` は、venv を有効にするコマンドです。
有効にすると、そのターミナルの `python` と `pip` が venv のものになります。
新しいターミナルを開いたときは、もう一度実行してください。
cron から実行するときは venv が有効にならないので、[examples/README.md](examples/README.md) の「サーバーごとに使う Python を指定する」の方法で Python を指定します。

### 4. インストールを確かめる

```bash
python -c 'import miopds_common; print(miopds_common.__file__)'
```

`~/mio_pds_validate/lib/python3.13/site-packages/miopds_common/__init__.py` のように venv の中のパスが表示されれば、インストールできています。
このコマンドは `~/miopds_common` の中では実行しないでください。
そこで実行すると、Python はインストールしたものではなく手元のソースを読み込むので、インストールしていなくてもパスが表示されます。

コードを編集しながら使う場合は、`pip install -e` でインストールします。
手順は [docs/usage_ja.md](docs/usage_ja.md) の「開発」にあります。

PDS Validate（検証に使う Java のツール）は、検証するときだけ必要です。
インストールの手順は [examples/README.md](examples/README.md) の「PDS Validate 4.2.0 のインストール」にあります。

## クイックスタート

### 準備

コマンドは、機器のリポジトリの一番上で実行します。
機器のリポジトリには、miopds_common の `examples/` をコピーし、`pds/` という名前で置きます。
データ（Bundle のディレクトリ）は、リポジトリの外に置きます。
以下の例では、Bundle を `~/pds4/bc_mmo_pwi/` に置き、PWI-EFD の見本の値（Bundle が `bc_mmo_pwi`、Collection が `data_calibrated_efd`）を使います。
ほかの機器では、名前と場所を読み替えてください。

```text
instrument_repo/                          # 機器のリポジトリ（例）
└── pds/                                  # miopds_common の examples/ をコピーしたもの
    ├── scripts/
    ├── templates/
    └── config/

~/pds4/
└── bc_mmo_pwi/                           # Bundle のディレクトリ
    └── data_calibrated_efd/              # Collection のディレクトリ
        ├── cruise/                       # Cruise のデータ
        │   └── sc/
        │       └── YYYY0101_YYYY1231/    # 年ごとのディレクトリ（CDF を置く）
        └── mercury_science_orbit/        # Mercury Science Phase のデータ
            └── sc/
                └── YYYY0101_YYYY1231/
```

観測ラベルは、CDF と同じディレクトリに作ります。

1. `examples/` を、`pds/` という名前で機器のリポジトリにコピーします。
   `pds/` がまだないときに実行してください（すでにあると、`pds/examples/` ができてしまいます）。

   ```bash
   cp -R ~/miopds_common/examples pds
   ```

2. `pds/config/dataset_pwi_efd.json` の `collection` にある3つの値（`title`、`citation_description`、`collection_description`）を書き換えます。
   見本には `REPLACE_` で始まる仮の値が入っています。
   仮の値が残っていると、このファイルを `--dataset-config` に指定したコマンドは、次のエラーで止まります。

   ```text
   ERROR: .../pds/config/dataset_pwi_efd.json.collection.title: placeholder 'REPLACE_COLLECTION_TITLE' must be replaced
   ```

   ほかの機器では、`instrument_*.json`、`dataset_*.json`、`authors_*.json` も機器に合わせて作ります。
   各項目の意味は [examples/config/README.md](examples/config/README.md) にあります。

3. venv を有効にします。

   ```bash
   source ~/mio_pds_validate/bin/activate
   ```

以下の例では、長いコマンドを `\` で複数の行に分けています。
行末の `\` は、コマンドが次の行に続くことを表します。

### 期間表を作る

観測ラベルのミッションフェーズを期間表で決めるときは、A の前に期間表（`mission_timeline.json`）を作ります。
期間表を使わないときは、この節を飛ばしてください。

期間表は、チームのミッションフェーズの表（`mission_phases.tab`）から作ります。
フェーズの期間は公開されていないので、表と期間表はリポジトリの外（この例では `~/pds_config/`）に置きます。

1. 置き場所のディレクトリを作ります（`mkdir -p` は、ディレクトリがすでにあれば何もしません）。

   ```bash
   mkdir -p ~/pds_config
   ```

2. `mission_phases.tab` をチームから入手し、`~/pds_config/` に置きます。

3. `tab2timeline` で、表を `mission_timeline.json` に変換します。

   ```bash
   python -m miopds_common tab2timeline ~/pds_config/mission_phases.tab ~/pds_config/mission_timeline.json
   ```

   引数は、変換する表、書き出す期間表の順です。
   表の最後のフェーズが `msp` でないときは、そのフェーズの終わりがわからないので、エラーになります。
   その場合は、`--end` で終わりの日時を指定します。
   表の形式と変換の決まりは、[examples/config/README.md](examples/config/README.md) の「.tab から変換する」にあります。

表が更新されたら、変換し直してください。
内容が変わっていないときは、`mission_timeline.json` を書き換えません。

### shell スクリプトを使う準備

A〜D の各手順は、Python のコマンドのほかに、`pds/scripts/` の shell スクリプトでも実行できます。
shell スクリプトは、テンプレートと設定ファイルを `pds/templates/` と `pds/config/` から読み、検証のレポートをリポジトリの `pds_chk_log/` に保存します。
Python のコマンドだけを使うときは、この節を飛ばしてください。

今のスクリプトは、次の4つの環境変数を指定しないと、この構成では動きません。
これは不具合で、[Issue #7](https://github.com/ergsc-devel/miopds_common/issues/7) で直す予定です。

| 環境変数 | 指定する値 | 使うスクリプト |
|---|---|---|
| `TIMELINE` | 期間表のファイル | 観測ラベル（A） |
| `MISSION_TIMELINE_FILE` | 期間表のファイル | Collection（B） |
| `ARCHIVE_ROOT` | Bundle のディレクトリを置いた場所 | Collection（B） |
| `VALIDATE_BIN` | PDS Validate の実行ファイル | Collection（B）、Bundle（C） |

期間表を使わない場合も、今のスクリプトは期間表のファイルがないと止まります。
上の「期間表を作る」で、先に期間表を作ってください。

`export` は、環境変数を設定して、そのターミナルでこのあと実行するコマンドに渡すコマンドです。
次の4つを順に実行します。
新しいターミナルを開いたときは、もう一度実行してください。

```bash
export TIMELINE=~/pds_config/mission_timeline.json
```

```bash
export MISSION_TIMELINE_FILE=~/pds_config/mission_timeline.json
```

```bash
export ARCHIVE_ROOT=~/pds4
```

```bash
export VALIDATE_BIN=~/local/pds/validate-4.2.0/bin/validate
```

観測ラベルのスクリプトを除き、shell スクリプトは作ったラベルを PDS Validate で検証します。
PDS Validate をまだインストールしていないときは、次のコマンドで検証を省けます。

```bash
export VALIDATE_ENABLED=0
```

### A. 観測ラベルだけを作る

CDF ファイル1つから、観測ラベルを1つ作ります。

#### Python のコマンドで実行する

```bash
python -m miopds_common cdf2pdslabel \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates/mmo_cdf_label_template_multi_dataset.xml.j2 \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231 \
  --mission-config pds/config/mission.json \
  --dataset-config pds/config/dataset_pwi_efd.json
```

引数は、CDF ファイル、テンプレート、出力先のディレクトリの順です。
ラベルの名前は、CDF のファイル名の `.cdf` を `.lblx` に変えたもの（この例では `bc_mmo_pwi-efd_l2_example_20270101_v01.lblx`）です。
CDF のファイル名には、`_20270101_` のように `_` で挟んだ8桁の日付が必要です。

Collection の CDF ファイルをすべて処理するときは、`for` で1つずつ繰り返します。

```bash
for cdf in ~/pds4/bc_mmo_pwi/data_calibrated_efd/*/sc/*/*.cdf; do
  python -m miopds_common cdf2pdslabel "$cdf" \
    pds/templates/mmo_cdf_label_template_multi_dataset.xml.j2 \
    "$(dirname "$cdf")" \
    --mission-config pds/config/mission.json \
    --dataset-config pds/config/dataset_pwi_efd.json
done
```

`*/sc/*/*.cdf` は、すべてのフェーズの、すべての年のディレクトリにある CDF に一致します。
`"$(dirname "$cdf")"` は、その CDF があるディレクトリです。ラベルは CDF と同じディレクトリにできます。

ミッションフェーズを指定しないと、`mission.json` の既定値（Mercury Science Phase、`msp`）がラベルに入ります。
上の「期間表を作る」で作った期間表を使うときは、`--timeline ~/pds_config/mission_timeline.json` を付けます。
すると、観測開始時刻が入る期間のフェーズがラベルに入ります。
期間表を使わずに、`--mission-phase-name` と `--mission-phase-id` を組で指定することもできます。
詳しくは [docs/usage_ja.md](docs/usage_ja.md) の「ミッションフェーズの期間表」を見てください。

#### shell スクリプトで実行する

`make_pds_label_for_mmo_cdf_data.sh` で、CDF ファイル1つから観測ラベルを1つ作ります。

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates "" \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231
```

| 順番 | 引数 | この例の値 |
|---|---|---|
| 1 | CDF ファイル | `~/pds4/.../bc_mmo_pwi-efd_l2_example_20270101_v01.cdf` |
| 2 | テンプレートのディレクトリ | `pds/templates` |
| 3 | テンプレートの名前（`""` にすると `mmo_cdf_label_template_multi_dataset.xml.j2`） | `""` |
| 4 | 出力先のディレクトリ | `~/pds4/.../20270101_20271231` |

5つ目以降の引数は、`cdf2pdslabel` のオプションとしてそのまま渡ります（例：`--mission-phase-name Cruise --mission-phase-id cruise`）。
設定ファイルは `pds/config/mission.json` と `pds/config/dataset_pwi_efd.json` を読みます（環境変数 `MISSION_CONFIG` と `DATASET_CONFIG` で変えられます）。
ミッションフェーズは、環境変数 `TIMELINE` の期間表から決まります。
このスクリプトは検証をしません。

Collection の CDF ファイルをすべて処理するときは、Python のコマンドと同じように `for` で繰り返します。

```bash
for cdf in ~/pds4/bc_mmo_pwi/data_calibrated_efd/*/sc/*/*.cdf; do
  ./pds/scripts/make_pds_label_for_mmo_cdf_data.sh "$cdf" pds/templates "" "$(dirname "$cdf")"
done
```

### B. 観測ラベルから Collection まで作る

A で作った観測ラベルを集めて、データの Collection のラベルとインベントリを作ります。

#### Python のコマンドで実行する

```bash
python -m miopds_common labels2collection \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd \
  pds/templates/collection_template.xml.j2 \
  urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd \
  data_calibrated_efd \
  --mission-config pds/config/mission.json \
  --dataset-config pds/config/dataset_pwi_efd.json \
  --publication-year 2027
```

| 順番 | 引数 | この例の値 |
|---|---|---|
| 1 | 観測ラベルを探すディレクトリ（サブディレクトリの中も探す） | `~/pds4/bc_mmo_pwi/data_calibrated_efd` |
| 2 | 出力先のディレクトリ | `~/pds4/bc_mmo_pwi/data_calibrated_efd` |
| 3 | テンプレート | `pds/templates/collection_template.xml.j2` |
| 4 | Collection の LID | `urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd` |
| 5 | 出力ファイルの名前（拡張子なし） | `data_calibrated_efd` |

1つ目の引数に Collection のディレクトリを指定すると、すべてのフェーズと年のディレクトリから観測ラベルを集めます。
前に作った Collection のラベルも同じディレクトリにありますが、インベントリには入りません。
出力は、`~/pds4/bc_mmo_pwi/data_calibrated_efd/` の `data_calibrated_efd.lblx`（ラベル）と `data_calibrated_efd.csv`（インベントリ）です。
CDF ファイルが見つからない観測ラベルは、警告を表示してインベントリから外します。

#### shell スクリプトで実行する

`create_psa_collection_jinja.sh` に Collection の名前を渡すと、Collection のラベルとインベントリを作り、Collection のラベルを検証します。

```bash
./pds/scripts/create_psa_collection_jinja.sh data_calibrated_efd
```

Collection のディレクトリは、`$ARCHIVE_ROOT/bc_mmo_pwi/data_calibrated_efd`（この例では `~/pds4/bc_mmo_pwi/data_calibrated_efd`）になります。
Bundle の名前は環境変数 `BUNDLE_NAME` で変えられます（既定は `bc_mmo_pwi`）。
検証のレポートは、`pds_chk_log/` に日時を付けて保存します。

macOS では、このスクリプトは `find: -printf: unknown primary or operator` で止まります（Issue #7）。
macOS では、上の Python のコマンドを使ってください。
Linux の `find` にはこの機能があるので止まらないはずですが、まだ確かめていません。

### C. Bundle まで作る

B で Collection を作った後、Bundle のディレクトリの下にある Collection のラベルを集めて、Bundle のラベルを作ります。

#### Python のコマンドで実行する

```bash
python -m miopds_common collections2bundle ~/pds4/bc_mmo_pwi \
  --template pds/templates/bundle_template.xml.j2 \
  --bundle-lid urn:jaxa:darts:bc_mmo_pwi \
  --mission-config pds/config/mission.json \
  --instrument-config pds/config/instrument_pwi.json \
  --publication-year 2027
```

出力は `~/pds4/bc_mmo_pwi/bc_mmo_pwi.lblx` です。
Document（PDF の文書）を Bundle に入れるときは、Bundle を作る前に `pdf2document` で Document のラベルと Document Collection を作ります。
手順は [docs/usage_ja.md](docs/usage_ja.md) の「pdf2document：Document と Document Collection」にあります。

#### shell スクリプトで実行する

Document を Bundle に入れるときは、Bundle を作る前に `create_psa_document_jinja.sh` を実行します。
`~/pds4/bc_mmo_pwi/document/` にある PDF（既定は `bc_mmo_pwi_data_user_guide.pdf`）から、Document のラベルと Document Collection を作り、検証します。

```bash
./pds/scripts/create_psa_document_jinja.sh ~/pds4/bc_mmo_pwi/document
```

PDF の名前や Document の題名は、環境変数で変えます（[examples/README.md](examples/README.md) の「Document」）。

次に、`create_psa_bundle_jinja.sh` に Bundle のディレクトリを渡して、Bundle のラベルを作ります。

```bash
./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

このスクリプトは、Bundle のラベルを作ったあと、Bundle 全体を PDS Validate で検証します（D の検証も、このスクリプトが行います）。
検証のレポートは、`pds_chk_log/` に日時を付けて保存します。

### D. 検証する

PDS Validate で Bundle 全体を検証し、画面に出た内容をリポジトリの `pds_chk_log/bundle_screen.log` に保存します。
shell スクリプトを使ったときは、C の `create_psa_bundle_jinja.sh` がこの検証を行うので、この手順はいりません。

```bash
python -m miopds_common validate ~/pds4/bc_mmo_pwi \
  --report pds_chk_log/bundle_screen.log \
  --validate-bin ~/local/pds/validate-4.2.0/bin/validate \
  --rule pds4.bundle \
  --label-extension lblx
```

`--validate-bin` には、PDS Validate の実行ファイルを指定します（この例は、`examples/README.md` の手順でインストールした場所です）。
検証の後は、終了コードにかかわらずレポートを読んでください。
理由は [docs/usage_ja.md](docs/usage_ja.md) の「既知の問題」にあります。

### まとめて実行する

`pds/scripts/cron_mk_cdf_to_pds.sh`（miopds_common では `examples/scripts/cron_mk_cdf_to_pds.sh`）は、A から D までと Document の作成を順に実行し、入力が変わった製品だけを作り直します。
cron で定期的に実行することを想定しています。
使い方は [examples/README.md](examples/README.md) を見てください。

ただし、今のスクリプトは Collection の下の `science/` を探すので、この構成では最初の段階で止まります（Issue #7）。

## 文書

| 文書 | 内容 |
|---|---|
| [docs/usage_ja.md](docs/usage_ja.md) | パッケージの手順書（サブコマンドとオプション、Python からの使い方、設定ファイル、検証、開発） |
| [examples/README.md](examples/README.md) | shell スクリプトと、その実行のしかた |
| [examples/config/README.md](examples/config/README.md) | 設定ファイルの項目と、ラベルのどこに入るか |
| [CONTRIBUTING.md](CONTRIBUTING.md) | git のブランチと、その運用（英語） |
