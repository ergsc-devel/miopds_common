# 設定ファイルの見本（examples/config）

[English](README.md)

`examples/config/` には、PDS4 のラベルを作るときに使う設定ファイル（JSON）の見本があります。
`examples/` ごと機器のリポジトリにコピーし（例：`pds/config/`）、機器とデータセットに合わせて書き換えて使います。

この文書では、設定ファイルの各項目の意味と、その値がラベルのどの要素に入るかを説明します。

## ファイルと使うサブコマンド

設定ファイルは、PDS4 アーカイブの構造に合わせて4つの階層に分けています。

| ファイル | 階層 | 対応する PDS4 の単位 | 読むサブコマンド（`python -m miopds_common ...`） |
|---|---|---|---|
| `mission.json` | ミッション（Mio/BepiColombo で共通） | — | すべて |
| `instrument_pwi.json` | 機器 | Bundle（例：`bc_mmo_pwi`） | `collections2bundle`、`pdf2document`。`cdf2pdslabel` は `dataset_*.json` の `instrument_file` から読む |
| `dataset_pwi_efd.json` | データセット | Data Collection（例：`data_calibrated_efd`） | `cdf2pdslabel`、`labels2collection` |
| `authors_pwi_efd.json` | 著者リスト | 観測ラベルの `List_Author` | `cdf2pdslabel`（`dataset_*.json` の `authors_file` から読む） |

`pdf2pdslabel` が読むのは `mission.json` だけです。
Document そのものの値（題名、PDF の名前など）は、コマンドの引数か shell の環境変数で指定します。

観測日からミッションフェーズとターゲットを決める期間表（`mission_timeline.json`）は、フェーズの期間が公開されていないので、このリポジトリには置きません。
作り方は、下の「ミッションフェーズとターゲットの決め方」を見てください。

## 共通の規則

- JSON にはコメントを書けません。各項目の意味は、この文書に書いています。
- 最後の要素の後ろにカンマを付けると、エラーになります（例：`["a", "b",]` は書けません）。
- 相対パスは、その JSON ファイルがあるディレクトリを基準に解釈します。コマンドを実行した場所は基準になりません。
- `REPLACE_` で始まる値は、書き換えが必要な仮の値です。
  1つでも残っていると、そのファイルを読み込んだ時点でエラーになります（そのコマンドが使わない項目でも同じです）。

  ```text
  ERROR: .../dataset_pwi_efd.json.collection.title: placeholder 'REPLACE_COLLECTION_TITLE' must be replaced
  ```

## 表の読み方（ラベルの種類と XML の場所）

以下の表は、JSON の各項目が、どのラベルの、どの XML の要素に入るかを示します。
ラベルは次の5種類です。

| 表での呼び方 | ラベル（一番外側の要素） | 作るサブコマンド |
|---|---|---|
| 観測 | 観測ラベル（`Product_Observational`）。CDF ごとに1つ | `cdf2pdslabel` |
| Collection | データの Collection のラベル（`Product_Collection`） | `labels2collection` |
| Bundle | Bundle のラベル（`Product_Bundle`） | `collections2bundle` |
| Document | 文書のラベル（`Product_Document`） | `pdf2pdslabel`、`pdf2document` |
| Document Collection | 文書の Collection のラベル（`Product_Collection`） | `pdf2document` |

- 「XML の場所」は、一番外側の要素のすぐ内側からのパスです。
  `A/B/c` は「`A` の中の `B` の中の `c`」という意味です。
- `psa:` や `msn:` で始まる要素は、PSA の辞書や Mission の辞書で定められた要素です（この印を名前空間の接頭辞といいます）。
- ラベルの要素から値の出どころを探すときは、下の「ラベルから逆引きする」を見てください。
  JSON 以外（CDF、コマンドの引数）から来る値も載せています。

## mission.json（ミッションで共通）

| 項目 | ラベル | XML の場所 | 説明 |
|---|---|---|---|
| `information_model_version` | すべて | `Identification_Area/information_model_version` | PDS4 Information Model の版 |
| `investigation.name` / `.type` / `.lid` | 観測、Document Collection | `Investigation_Area` の `name` / `type` / `Internal_Reference/lid_reference`。`Investigation_Area` は、観測では `Observation_Area` の中、Document Collection では `Context_Area` の中 | ミッション（BepiColombo）の情報 |
| `instrument_host.name` / `.lid` | 観測 | `Observation_Area/Observing_System/Observing_System_Component`（`type` が `Host` のもの）の `name` / `Internal_Reference/lid_reference` | 探査機（MMO）の情報 |
| `cdf_parsing_standard_id` | 観測 | `File_Area_Observational/Header/parsing_standard_id` | CDF のヘッダーの解釈の規格 |
| `default_mission_phase.name` | 観測 | `Observation_Area/Mission_Area/psa:Mission_Information/psa:Mission_Phase/psa:name` と `Observation_Area/Discipline_Area/msn:Mission_Information/msn:mission_phase_name` の2か所 | 既定のミッションフェーズの名前 |
| `default_mission_phase.id` | 観測 | `Observation_Area/Mission_Area/psa:Mission_Information/psa:Mission_Phase/psa:id` | 既定のミッションフェーズの ID |
| `default_target.name` / `.type` / `.lid` | 観測 | `Observation_Area/Target_Identification` の `name` / `type` / `Internal_Reference/lid_reference` | 既定のターゲット |

`default_mission_phase` と `default_target` は、コマンドの引数でも期間表でも決まらないときに使う値です（下の「ミッションフェーズとターゲットの決め方」）。

## instrument_pwi.json（機器 = Bundle の単位）

| 項目 | ラベル | XML の場所 | 説明 |
|---|---|---|---|
| `instrument.name` | 観測、Document Collection | 観測：`Observation_Area/Observing_System/Observing_System_Component`（`type` が `Instrument` のもの）の `name`。Document Collection：`Context_Area/Observing_System/Observing_System_Component/name` | 機器の名前 |
| `instrument.lid` | 観測 | 上の観測の `Observing_System_Component` の `Internal_Reference/lid_reference` | 機器の context 製品の LID |
| `bundle.title` | Bundle | `Identification_Area/title` | Bundle の題名 |
| `bundle.description` | Bundle | `Identification_Area/Citation_Information/description` | Bundle の説明 |
| `document_collection.title` | Document Collection | `Identification_Area/title` | 題名 |
| `document_collection.citation_description` | Document Collection | `Identification_Area/Citation_Information/description` | 引用のための説明 |
| `document_collection.collection_description` | Document Collection | `Collection/description` | Collection の説明 |

機器の名前と機器の LID の組は、BepiColombo の辞書の規則で決められています（例：PWI は `urn:jaxa:darts:context:instrument:mmo.pwi`）。

## dataset_pwi_efd.json（データセット = Data Collection の単位）

| 項目 | ラベル | XML の場所 | 説明 |
|---|---|---|---|
| `instrument_file` | — | — | 機器の設定ファイルへのパス（このファイルからの相対パス） |
| `authors_file` | — | — | 著者リストへのパス（このファイルからの相対パス） |
| `purpose` | 観測 | `Observation_Area/Primary_Result_Summary/purpose` | データの目的 |
| `processing_level` | 観測 | `Observation_Area/Primary_Result_Summary/processing_level` | 処理レベル |
| `science_facets.domains` | 観測 | `Observation_Area/Primary_Result_Summary/Science_Facets/domain` | 対象の領域のリスト。リストの要素ごとに `domain` が1つずつ入る |
| `science_facets.discipline_name` | 観測 | `Observation_Area/Primary_Result_Summary/Science_Facets/discipline_name` | 分野 |
| `science_facets.facet1` / `.facet2` | 観測 | `Observation_Area/Primary_Result_Summary/Science_Facets/facet1` / `facet2` | 分野の細分類。当てはまらないときは項目ごと省く（要素も出力されない。空文字はエラー） |
| `cdf.time_variable` | 観測 | `Observation_Area/Time_Coordinates/start_date_time` / `stop_date_time` | 変数の名前はラベルに入らない。この CDF 変数の最初と最後の値が、観測の開始と終了の時刻として入る |
| `cdf.epoch_variable` | — | — | ラベルには入らない。time 変数とレコード数が同じかの確認と、配列の時間軸の要素数に使う |
| `collection.collection_type` | Collection | `Collection/collection_type` | Collection の種類 |
| `collection.title` | Collection | `Identification_Area/title` | 題名 |
| `collection.citation_description` | Collection | `Identification_Area/Citation_Information/description` | 引用のための説明 |
| `collection.collection_description` | Collection | `Collection/description` | Collection の説明 |

`purpose`、`processing_level`、Science_Facets の各項目に書ける値は、PDS4 の規格で決められています。
誤った値は、PDS Validate で見つかります。

このファイルは、1つの Data Collection に入るデータセットが1種類だけ、という前提で、Collection の題名と説明を持っています。
1つの Collection に複数のデータセットを入れる場合は、この形では書けません。

## authors_*.json（著者リスト）

著者リストは、オブジェクトのリストです。
各要素には次の3つの項目がすべて必要で、空文字は使えません。
著者リストが入るのは観測ラベルだけです（Collection、Bundle、Document のラベルには入りません）。
リストの要素ごとに `Person` が1つずつ、書いた順に入ります。

| 項目 | ラベル | XML の場所 | 例 |
|---|---|---|---|
| `display_full_name` | 観測 | `Identification_Area/Citation_Information/List_Author/Person/display_full_name` | `"Shinbori, A."` |
| `given_name` | 観測 | `Identification_Area/Citation_Information/List_Author/Person/given_name` | `"A."` |
| `family_name` | 観測 | `Identification_Area/Citation_Information/List_Author/Person/family_name` | `"Shinbori"` |

`authors_instrument_example.json` がひな形、`authors_pwi_efd.json` が記入例です。

## ラベルから逆引きする

ラベルの要素ごとに、値の出どころを示します。
図の「引数」は、`python -m miopds_common SUBCOMMAND` のオプションです（shell スクリプトでは、環境変数や引数から渡されます）。

`logical_identifier` には、ID の部分だけではなく、LID 全体が入ります。
LID は、接頭辞のあとに Bundle ID、Collection ID、製品 ID を、製品の階層に応じてコロン（`:`）で区切ってつないだものです。

| 製品 | LID の形 | 例 |
|---|---|---|
| Bundle | `接頭辞:Bundle ID` | `urn:jaxa:darts:bc_mmo_pwi` |
| Collection | `接頭辞:Bundle ID:Collection ID` | `urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd` |
| 製品（観測データ、文書） | `接頭辞:Bundle ID:Collection ID:製品 ID` | `urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide` |

shell スクリプトでは、`BUNDLE_NAME` が Bundle ID、`create_psa_collection_jinja.sh` の1つ目の引数（`COLLECTION_NAME`）が Collection ID です。
shell スクリプトは、これらに接頭辞 `urn:jaxa:darts` を付けて LID 全体を作ります（`BUNDLE_LID` と `COLLECTION_LID` で、LID 全体を直接指定することもできます）。

LID の決まりは、PDS4 Data Provider's Handbook 1.22.0 に書かれています。
使える文字（小文字の英字、数字、`-`、`.`、`_`。`:` は区切りにだけ使う）と長さ（255文字まで）は 5.1 節（p.21）に、組み立て方は 5.2 節（p.22）にあります。
すべての決まりは、Handbook が参照している Standards Reference の 6D.2 節にあります。
接頭辞の `urn:jaxa:darts` は JAXA の決まりで、Handbook には書かれていません（Handbook の例は `urn:nasa:pds` と `urn:esa:psa` です）。

### 観測ラベル（Product_Observational）

```text
Product_Observational
├─ Identification_Area
│  ├─ logical_identifier .......... CDF の属性 PDS_LOGICAL_IDENTIFIER（製品の LID 全体。YYYYMMDD はファイル名の日付に置き換え）
│  ├─ version_id .................. CDF の属性 PDS_VERSION_IDENTIFIER（なければ 1.0）
│  ├─ title ....................... CDF の属性 TITLE（なければ CDF のファイル名から拡張子を除いたもの）
│  ├─ information_model_version ... mission.json: information_model_version
│  ├─ Citation_Information
│  │  ├─ publication_year ......... 引数 --publication-year（なければ CDF の更新日時の年）
│  │  ├─ description .............. 引数 --description（なければ CDF の属性 Logical_source_description、次に TITLE）
│  │  └─ List_Author/Person ....... authors_*.json（dataset_*.json の authors_file）
│  └─ Modification_History ........ 実行した日（UTC）と、引数 --modification-description
├─ Observation_Area
│  ├─ Time_Coordinates ............ CDF 変数（dataset_*.json: cdf.time_variable）の最初と最後の値
│  ├─ Primary_Result_Summary ...... dataset_*.json: purpose、processing_level、science_facets
│  ├─ Investigation_Area .......... mission.json: investigation
│  ├─ Observing_System
│  │  ├─ Component（type が Host） ......... mission.json: instrument_host
│  │  └─ Component（type が Instrument） ... instrument_*.json: instrument（dataset_*.json の instrument_file）
│  ├─ Target_Identification ....... 引数 --target-* → 期間表の targets → mission.json: default_target（この優先順）
│  ├─ Mission_Area
│  │  ├─ psa:Mission_Information
│  │  │  ├─ psa:spacecraft_clock_start_count / stop_count ... CDF の属性 PDS_SCLK_START_COUNT / PDS_SCLK_STOP_COUNT
│  │  │  └─ psa:Mission_Phase ..... 引数 --mission-phase-* → 期間表の mission_phases → mission.json: default_mission_phase
│  │  └─ psa:Processing_Context ... CDF の属性 GENERATION_SOFTWARE、SOFTWARE_VERSION、SOURCE_FILE
│  └─ Discipline_Area/msn:Mission_Information ... ミッションフェーズの名前と SCLK（上と同じ値）
├─ Reference_List ................. 引数 --internal-reference（指定したときだけ出力）
└─ File_Area_Observational
   ├─ File ........................ CDF ファイルそのもの（名前、更新日時、サイズ、MD5）
   ├─ Header ...................... 引数 --header-length、mission.json: cdf_parsing_standard_id
   └─ Array / Table_Binary ........ CDF の各変数（名前、位置、型、属性 CATDESC・UNITS・FILLVAL・VALIDMIN・VALIDMAX）
```

### データの Collection（Product_Collection）

```text
Product_Collection
├─ Identification_Area
│  ├─ logical_identifier .......... 引数（Collection の LID 全体。shell は urn:jaxa:darts:BUNDLE_NAME:COLLECTION_NAME から作る）
│  ├─ version_id .................. 引数 --version-id
│  ├─ title ....................... dataset_*.json: collection.title
│  ├─ information_model_version ... mission.json: information_model_version
│  └─ Citation_Information
│     ├─ publication_year ......... 引数 --publication-year
│     └─ description .............. dataset_*.json: collection.citation_description
├─ Collection
│  ├─ collection_type ............. dataset_*.json: collection.collection_type
│  └─ description ................. dataset_*.json: collection.collection_description
└─ File_Area_Inventory ............ 作ったインベントリ（.csv）の名前、サイズ、MD5、行数
```

### Bundle（Product_Bundle）

```text
Product_Bundle
├─ Identification_Area
│  ├─ logical_identifier .......... 引数 --bundle-lid（Bundle の LID 全体。shell は urn:jaxa:darts:BUNDLE_NAME から作る）
│  ├─ version_id .................. 引数 --version-id
│  ├─ title ....................... instrument_*.json: bundle.title
│  ├─ information_model_version ... mission.json: information_model_version
│  ├─ Citation_Information
│  │  ├─ publication_year ......... 引数 --publication-year
│  │  └─ description .............. instrument_*.json: bundle.description
│  └─ Modification_History ........ 引数 --modification-date（なければ実行した日）、--modification-description
├─ Bundle/bundle_type ............. 固定（Archive）
└─ Bundle_Member_Entry ............ Bundle のディレクトリの下で見つけた Collection のラベル（LID と種類）
```

### Document と Document Collection

| ラベル | JSON から来る値 | それ以外 |
|---|---|---|
| Document（`Product_Document`） | mission.json：`information_model_version` | LID、題名、説明、出版年と出版日、版、言語、PDF のファイル名は、すべて引数 |
| Document Collection（`Product_Collection`） | mission.json：`information_model_version`、`investigation`。instrument_*.json：`instrument.name`、`document_collection` の3項目 | LID、版、出版年、変更履歴は引数。`collection_type` は固定（Document） |

## ミッションフェーズとターゲットの決め方

観測ラベルのミッションフェーズとターゲットは、次の優先順で決まります。

1. コマンドの引数（`--mission-phase-name`、`--mission-phase-id`、`--target-name` など）
2. 期間表（`mission_timeline.json`）。指定したときだけ使う。観測開始時刻が入る期間の値を使い、どの期間にも入らないときはエラーにする
3. `mission.json` の `default_mission_phase` と `default_target`

Python のコマンドで期間表を使わないときは、Mercury Science Phase（`msp`）以外の期間のデータに、1 の引数を指定してください。
指定しないと、既定値のままラベルに入ります。
今の shell スクリプトは、期間表のファイルがないと動きません（[../README_ja.md](../README_ja.md) の「今のスクリプトに必要な設定」）。

### mission_timeline.json の書式

```json
{
  "mission_phases": [
    {"start": "YYYY-MM-DDThh:mm:ssZ", "stop": "YYYY-MM-DDThh:mm:ssZ", "name": "Cruise", "id": "cruise"}
  ],
  "targets": [
    {"start": "YYYY-MM-DDThh:mm:ssZ", "stop": "YYYY-MM-DDThh:mm:ssZ",
     "name": "Mercury", "type": "Planet", "lid": "urn:nasa:pds:context:target:planet.mercury"}
  ]
}
```

- フェーズとターゲットは切り替わる時期が違うので、別々のリストにしています。
- 各期間は「start 以上 stop 未満」です。境界の時刻ちょうどは、後の期間に入ります。
- 期間の境界をまたぐ製品は、観測開始時刻で判定します。
- 期間が重なっているときと、start が stop 以降のときは、読み込んだ時点でエラーになります。
- 日時にタイムゾーンがないときは、UTC とみなします。

各項目が入るのは観測ラベルだけで、場所は `mission.json` の既定値と同じです（`mission_phases[]` は「`mission_phases` のリストの各要素」という意味です）。

| 項目 | ラベル | XML の場所 |
|---|---|---|
| `mission_phases[].name` | 観測 | `default_mission_phase.name` と同じ2か所 |
| `mission_phases[].id` | 観測 | `default_mission_phase.id` と同じ場所 |
| `targets[].name` / `.type` / `.lid` | 観測 | `default_target` と同じ場所 |
| `start` / `stop` | — | ラベルには入らない。観測開始時刻がどの期間に入るかの判定に使う |

### mission_timeline.json の置き場所と使い方

フェーズの期間は公開されていないので、本物の期間表はサーバーにだけ置き、git では管理しません。

1. 期間表を作り、サーバーのリポジトリの外に置きます（例：`~/pds_config/mission_timeline.json`）。
   作り方は2通りあります。
   - チームのミッションフェーズの表（`.tab`）から変換する（下の「.tab から変換する」）
   - 上の書式のとおりにファイルを作り、本物の日時を書く
2. 期間表を使うときは、Python のコマンドでは `--timeline` にそのパスを指定します。
   今の shell スクリプトでは、環境変数 `TIMELINE`（観測ラベル）と `MISSION_TIMELINE_FILE`（Collection）に指定します（[../README_ja.md](../README_ja.md) の「今のスクリプトに必要な設定」）。
   cron で実行するときは、これらの環境変数を crontab の行に書きます。

期間表を書くときの決まりは、次のとおりです。

- `.gitignore` は、`mission_timeline.json` と `mission_*.tab` という名前のファイルを除外します。
  誤ってリポジトリの中に置いても push はされませんが、名前を変えると除外されないので、置き場所はリポジトリの外にしてください。
- データの全期間を、すき間なく書いてください。どの期間にも入らない観測があると、エラーになります。
- 終わりが決まっていないフェーズの `stop` には、遠い未来の日時（例：`2100-01-01T00:00:00Z`）を入れます。
- `targets` は省略できます。省略すると、ターゲットは `mission.json` の `default_target` になります。

### .tab から変換する（tab2timeline）

チームのミッションフェーズの表（`.tab`。日付は非公開）から、`mission_timeline.json` を作ります。
この例では、表 `mission_phases.tab` を `~/pds_config/` に置いています。

```bash
python -m miopds_common tab2timeline ~/pds_config/mission_phases.tab ~/pds_config/mission_timeline.json
```

表は、1行が1つのフェーズの始まりを表します。
列はカンマで区切り、空白で幅をそろえてあります。

```text
# Start Time            ,Mission Phase Acronym ,Mission Phase Name ,Path to folder
YYYY-MM-DDThh:mm:ss.sssZ ,cruise                ,Cruise             ,cruise
```

| 表の列 | `mission_timeline.json` での使い方 |
|---|---|
| Start Time | そのフェーズの `start`。前のフェーズの `stop` にもなる |
| Mission Phase Acronym | `id` |
| Mission Phase Name | `name` |
| Path to folder | 使わない |

変換は、次の決まりで行います。

- `#` で始まる行（ヘッダー）と空行は、読み飛ばします。
- 各フェーズの `stop` は、次のフェーズの `Start Time` です。同じフェーズが続く行は、1つの期間にまとめます。
- 最後のフェーズは `msp` でなければなりません。その `stop` は `2100-01-01T00:00:00Z` になります（`--end` で変えられます）。
  最後が `msp` 以外の表は、終わりがわからないのでエラーになります。そのフェーズの終わりの日時を `--end` で指定すれば、変換できます。
- `Start Time` が増えていない行、列の数が4つでない行、日時の書式が正しくない行は、エラーになります（エラーには行番号が出ます）。
- 書き出す前に、使うときと同じ確認（期間の重なりなど）をします。
- 略称（Mission Phase Acronym）が PSA の辞書の ID と同じ綴りかは、確かめません。
  初めて変換したときは、出てきた略称を、下の「ミッションフェーズとして使える値」と見比べてください。
- 表が変わったら、変換し直してください。
  内容が変わったときだけ `mission_timeline.json` を書き換えるので、`cron_mk_cdf_to_pds.sh` は次の実行で観測ラベルを作り直します。
  内容が変わらないときは書き換えない（ファイルの日時も変わらない）ので、cron で毎回変換しても、観測ラベルが毎回作り直されることはありません。

### ミッションフェーズとして使える値

使える name と id の組は、PSA が公開している BepiColombo のミッション辞書のスキーマトロンで決められています。

- https://psa.esa.int/psa/bc/v1/PDS4_BC_1M00_2010.sch
  （2026-10-01 に、辞書の版 2.0.1.0 で確かめました。辞書の版が上がると変わることがあるので、配信に使う辞書の版で確かめてください）

例：`Cruise` / `cruise`、`Mercury Orbit Commissioning Phase` / `mocp`、`Mercury Science Phase` / `msp`

一覧にない値は、PDS Validate でエラーになります。
