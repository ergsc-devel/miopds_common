# config

PDS4 ラベル生成に使う設定ファイル（JSON）の見本です。
各機器のリポジトリにコピーし、機器・データセットに合わせて書き換えて使います。

> **使うサブコマンド**（`python -m miopds_common ...`）：`cdf2pdslabel`（mission、dataset）、
> `labels2collection`（mission、dataset）、`collections2bundle`（mission、instrument）、
> `pdf2pdslabel` と `pdf2document`（mission、instrument）。
> Document 製品そのものの値（title、PDF のファイル名など）は、コマンド引数や shell の環境変数で指定します。

## ファイルの構成

PDS4 アーカイブの構造に合わせて、4つの階層に分けています。

| ファイル | 階層 | 対応する PDS4 の単位 |
|---|---|---|
| `mission.json` | ミッション（Mio/BepiColombo 共通） | — |
| `instrument_pwi.json` | 機器 | Bundle（例：`bc_mmo_pwi`） |
| `dataset_pwi_efd.json` | データセット | Data Collection（例：`data_calibrated_efd`） |
| `authors_pwi_efd.json` | 著者リスト | 各ラベルの `List_Author` |

`mission_timeline.json`（観測日でミッションフェーズとターゲットを決める期間表）は、
期間の出典が未確定のため、見本を置いていません。書式は下の「ミッションフェーズとターゲットの決め方」を参照してください。

## 共通の規則

- **JSON にはコメントを書けません。** 各項目の意味はこの README に書いています。
- **最後の要素の後ろにカンマを付けるとエラーになります**（例：`["a", "b",]` は不可）。
- **相対パスは、その JSON ファイルが置かれているディレクトリを基準に解釈します。**
  実行した場所（カレントディレクトリ）は基準になりません。
- **`REPLACE_` で始まる値はプレースホルダーです。** 使う前に必ず書き換えてください。
  1つでも残っていると、そのファイルを読み込んだ時点でエラーになります
  （そのコマンドが使わない項目でも同じです）。例：
  `ERROR: .../dataset_pwi_efd.json.collection.title: placeholder 'REPLACE_COLLECTION_TITLE' must be replaced`

## mission.json（ミッション共通）

| 項目 | 入る場所（ラベルの XML 要素） | 説明 |
|---|---|---|
| `information_model_version` | `Identification_Area/information_model_version` | PDS4 Information Model のバージョン |
| `investigation.name` / `.type` / `.lid` | `Investigation_Area` の `name` / `type` / `lid_reference` | ミッション（BepiColombo）の情報 |
| `instrument_host.name` / `.lid` | `Observing_System_Component`（type が Host）の `name` / `lid_reference` | 探査機（MMO）の情報 |
| `cdf_parsing_standard_id` | `File_Area_Observational/Header/parsing_standard_id` | CDF ヘッダーの解釈規格 |
| `default_mission_phase.name` / `.id` | `psa:Mission_Phase` の `psa:name` / `psa:id`、`msn:mission_phase_name` | 既定のミッションフェーズ |
| `default_target.name` / `.type` / `.lid` | `Target_Identification` の `name` / `type` / `lid_reference` | 既定のターゲット |

## instrument_pwi.json（機器 = Bundle 単位）

| 項目 | 入る場所 | 説明 |
|---|---|---|
| `instrument.name` / `.lid` | 観測ラベルの `Observing_System_Component`（type が Instrument） | 機器名と、機器の context 製品の LID |
| `bundle.title` / `.description` | Bundle ラベルの `title` / `Citation_Information/description` | Bundle の題名と説明 |
| `document_collection.title` | Document Collection ラベルの `title` | 題名 |
| `document_collection.citation_description` | 同 `Citation_Information/description` | 引用用の説明 |
| `document_collection.collection_description` | 同 `Collection/description` | Collection の説明 |

機器名と機器 LID の組み合わせは、BepiColombo 辞書の規則で決められています
（例：PWI は `urn:jaxa:darts:context:instrument:mmo.pwi`）。

## dataset_pwi_efd.json（データセット = Data Collection 単位）

| 項目 | 入る場所 | 説明 |
|---|---|---|
| `instrument_file` | — | 機器ファイルへのパス（このファイルからの相対パス） |
| `authors_file` | — | 著者リストへのパス（このファイルからの相対パス） |
| `purpose` | `Primary_Result_Summary/purpose` | データの目的 |
| `processing_level` | `Primary_Result_Summary/processing_level` | 処理レベル |
| `science_facets.domains` | `Science_Facets/domain`（複数可） | 対象領域のリスト |
| `science_facets.discipline_name` | `Science_Facets/discipline_name` | 分野 |
| `science_facets.facet1` / `.facet2` | `Science_Facets/facet1` / `facet2` | 分野の細分類。該当しない場合は項目ごと省略する |
| `cdf.time_variable` | （ラベルには入らない） | 観測開始・終了時刻を読み取る CDF 変数名 |
| `cdf.epoch_variable` | （ラベルには入らない） | レコード数の確認に使う epoch 変数名 |
| `collection.collection_type` | Collection ラベルの `Collection/collection_type` | Collection の種類 |
| `collection.title` | 同 `title` | 題名 |
| `collection.citation_description` | 同 `Citation_Information/description` | 引用用の説明 |
| `collection.collection_description` | 同 `Collection/description` | Collection の説明 |

`purpose`、`processing_level`、Science_Facets の各項目に書ける値は、PDS4 の規格で決められています。
誤った値は PDS Validate で検出されます。

> **未確認の前提**：「1つの Data Collection には、profile が同じデータセットが1種類だけ入る」と仮定して、
> Collection の説明をこのファイルに持たせています。1つの Collection に複数のデータセットが入る場合は、
> Collection の説明を別ファイルに分ける必要があります。

## authors_*.json（著者リスト）

オブジェクトのリストです。各要素には次の3項目がすべて必要で、空文字は使えません。

| 項目 | 入る場所 | 例 |
|---|---|---|
| `display_full_name` | `List_Author/Person/display_full_name` | `"Shinbori, A."` |
| `given_name` | `List_Author/Person/given_name` | `"A."` |
| `family_name` | `List_Author/Person/family_name` | `"Shinbori"` |

`authors_instrument_example.json` がひな形、`authors_pwi_efd.json` が記入例です。

## ミッションフェーズとターゲットの決め方

次の優先順位で決めます。

1. **コマンドの引数**（`--mission-phase-name`、`--mission-phase-id`、`--target-name` など）
2. **`mission_timeline.json`**：指定した場合だけ使う。観測開始時刻が入る期間の値を使い、
   どの期間にも入らない場合はエラーにする
3. **`mission.json` の `default_mission_phase` / `default_target`**

timeline がない間は、既定値（Mercury Science Phase / `msp`）以外の期間のデータを処理するとき、
1 の引数を必ず指定してください。指定を忘れると、既定値のまま出力されます。

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

- フェーズとターゲットは切り替わる時期が異なるため、別々のリストにしています。
- 各期間は「start 以上 stop 未満」です。境界の時刻ちょうどは、後の期間に入ります。
- 期間の境界をまたぐ製品は、観測開始時刻で判定します（PSA の規則は未確認）。
- 期間が重なっている場合や、start が stop 以降の場合は、読み込み時にエラーになります。
- 日時にタイムゾーンがない場合は UTC とみなします。

### ミッションフェーズとして使える値

使える name と id の組は、PSA が公開している BepiColombo ミッション辞書のスキーマトロンで決められています。

- https://psa.esa.int/psa/bc/v1/PDS4_BC_1M00_2010.sch
  （2026-10-01 に辞書バージョン 2.0.1.0 で確認。**辞書のバージョンアップで変わることがある**ので、
  必ず配信に使う辞書のバージョンで確認してください）

例：`Cruise` / `cruise`、`Mercury Orbit Commissioning Phase` / `mocp`、`Mercury Science Phase` / `msp`

一覧にない値は PDS Validate でエラーになります。
