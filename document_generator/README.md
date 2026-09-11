# PDS4 Document Generator

Product_Document、Document Collection Inventory CSV、Product_Collectionを一括生成し、Document製品とCollectionラベルを個別検証します。

```bash
./create_psa_document_jinja.sh /var/www/html/data/chs/satellite/mmo/pds4/bc_mmo_pwi/document
```

レポート保存先:

```text
/home/miosc/mio-sc/work_local/tmp/pds_chk_log
```

生成物:

- `bc_mmo_pwi_data_user_guide.xml`
- `collection_bc_mmo_pwi_document.csv`
- `collection_bc_mmo_pwi_document.xml`
