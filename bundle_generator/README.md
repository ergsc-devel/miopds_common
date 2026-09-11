# bundle-generator

Collectionラベルを再帰検索してJinja2からBundle XMLを生成し、PDS ValidateでBundle全体を検証します。

## セットアップ

```bash
python3 -m pip install -r bundle-generator/requirements.txt
chmod +x bundle-generator/create_psa_bundle_jinja.sh
```

## PDS Validate 4.0.8のインストール

1. Javaを確認します。

```bash
java -version
```

2. NASA PDS ValidateのReleasesページからValidate 4.0.8のZIPまたはtar.gzを取得します。

- https://github.com/NASA-PDS/validate/releases
- https://nasa-pds.github.io/validate/

3. ホームディレクトリへ展開します。

```bash
cd "$HOME"
tar -xzf /path/to/validate-4.0.8.tar.gz
# ZIPの場合
unzip /path/to/validate-4.0.8.zip
```

4. 実行権限と起動を確認します。

```bash
chmod +x "$HOME/validate-4.0.8/bin/validate"
"$HOME/validate-4.0.8/bin/validate" --help
```

Java要件は、Validate 4.0.8配布物のリリースノートを優先してください。

## 実行

```bash
./bundle-generator/create_psa_bundle_jinja.sh [BUNDLE_DIR]
```

引数を省略した場合は`bc_mmo_pwi`を使用します。

```bash
./bundle-generator/create_psa_bundle_jinja.sh bc_mmo_pwi
```

生成先:

```text
bc_mmo_pwi/bundle_bc_mmo_pwi.xml
```

## Bundle検証

生成後、次の形式でBundleディレクトリ全体を検証します。

```bash
~/validate-4.0.8/bin/validate \
  --rule pds4.bundle \
  --target bc_mmo_pwi \
  --catalog pds4-validate-catalog.xml \
  --label-extension lblx
```

XML Catalogを絶対パスで指定する例:

```bash
VALIDATE_CATALOG=/absolute/path/pds4-validate-catalog.xml \
./bundle-generator/create_psa_bundle_jinja.sh bc_mmo_pwi
```

主な環境変数:

- `BUNDLE_LID`
- `BUNDLE_VID`
- `PUBLICATION_YEAR`
- `AUTHOR_LIST`
- `MODIFICATION_DATE`
- `OUTPUT_FILE`
- `TEMPLATE_FILE`
- `VALIDATE_ENABLED`
- `VALIDATE_BIN`
- `VALIDATE_CATALOG`
- `VALIDATE_LABEL_EXTENSION`
- `VALIDATE_REPORT`

検証を省略する場合:

```bash
VALIDATE_ENABLED=0 ./bundle-generator/create_psa_bundle_jinja.sh bc_mmo_pwi
```

`create_psa_bundle_jinja.sh`には、各設定、入力確認、Bundle生成、Validation実行について日本語コメントを付けています。
