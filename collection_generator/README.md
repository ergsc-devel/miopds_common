# collection-generator

## Python依存関係
```bash
python3 -m pip install -r collection-generator/requirements.txt
chmod +x collection-generator/create_psa_collection_jinja.sh
```

## PDS Validate 4.0.8のインストール
PDS ValidateはJava製のコマンドラインツールです。NASA PDSのReleasesページからValidate 4.0.8の配布アーカイブを取得してください。

- Releases: https://github.com/NASA-PDS/validate/releases
- 公式ドキュメント: https://nasa-pds.github.io/validate/

1. Javaを確認します。
```bash
java -version
```
2. ダウンロードした配布物をホームディレクトリへ展開します。
```bash
cd "$HOME"
tar -xzf /path/to/validate-4.0.8.tar.gz
# ZIPの場合
unzip /path/to/validate-4.0.8.zip
```
3. 実行権限と起動を確認します。
```bash
chmod +x "$HOME/validate-4.0.8/bin/validate"
"$HOME/validate-4.0.8/bin/validate" --help
```
配布物の展開後のディレクトリ名が異なる場合は、実際のパスを`VALIDATE_BIN`に指定してください。Java要件は4.0.8配布物のリリースノートを優先してください。

## XML Catalog
PSA/BepiColombo辞書を解決する`pds4-validate-catalog.xml`を用意し、絶対パスで指定することを推奨します。
```bash
VALIDATE_CATALOG=/absolute/path/pds4-validate-catalog.xml \
./collection-generator/create_psa_collection_jinja.sh data_calibrated_efd bc_mmo_pwi
```

## 実行
```bash
./collection-generator/create_psa_collection_jinja.sh [COLLECTION_NAME] [COLLECTION_DIR]
```
既定値は`data_calibrated_efd`と`bc_mmo_pwi`です。生成後、次の形式で自動検証します。
```bash
~/validate-4.0.8/bin/validate \
 --target bc_mmo_pwi/data_calibrated_efd/collection_bc_mmo_pwi_data_calibrated_efd.xml \
 --catalog pds4-validate-catalog.xml \
 --label-extension lblx
```
検証を省略する場合は`VALIDATE_ENABLED=0`を指定します。

## シェルスクリプト内のコメント

`create_psa_collection_jinja.sh`には、変数設定、入力確認、Collection生成、PDS Validate実行、レポート保存の各処理について、日本語コメントを追加しています。
