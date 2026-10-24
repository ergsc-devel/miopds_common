# Sample shell scripts and templates (examples)

[日本語](README_ja.md)

`examples/` is a set of samples for making the PSA/PDS4 archive with
miopds_common. It holds shell scripts, Jinja2 templates and config files
(JSON). Copy it into each instrument repository (e.g. `instrument_repo`) under
the name `pds/`, and adapt it to the instrument.

This document is a reference for the arguments, environment variables and
outputs of each script. For the steps to run everything from the beginning,
see "Quick start" in [../README.md](../README.md). This document also assumes
the directory layout of the quick start (the bundle is outside the repository,
at `~/pds4/bc_mmo_pwi/`). The command examples are run at the top of the
instrument repository.

The samples have values for BepiColombo Mio PWI (such as `bc_mmo_pwi`) as
their defaults. For other instruments, replace them with the values of the
instrument after copying.

## Contents

```text
examples/
├── scripts/     # shell scripts
├── templates/   # Jinja2 templates (*.xml.j2)
└── config/      # config files (*.json)
```

| File | Purpose |
|---|---|
| `scripts/make_pds_label_for_mmo_cdf_data.sh` | Makes one observational label (`.lblx`) from one CDF file |
| `scripts/create_psa_collection_jinja.sh` | Makes the label and inventory of a data Collection, and validates them |
| `scripts/create_psa_document_jinja.sh` | Makes the Document label and the Document Collection, and validates them |
| `scripts/create_psa_bundle_jinja.sh` | Makes the Bundle label, and validates the whole Bundle |
| `scripts/cron_mk_cdf_to_pds.sh` | Calls the four scripts above in order, and rebuilds only the products whose inputs have changed (meant to be run regularly by cron) |
| `templates/mmo_cdf_label_template_multi_dataset.xml.j2` | Template of the observational label |
| `templates/collection_template.xml.j2` | Template of the data Collection label |
| `templates/document_template.xml.j2` | Template of the Document label |
| `templates/document_collection_template.xml.j2` | Template of the Document Collection label |
| `templates/bundle_template.xml.j2` | Template of the Bundle label |
| `config/mission.json` | Mission settings (shared by all Mio instruments) |
| `config/instrument_pwi.json` | Instrument settings (filled in for PWI) |
| `config/dataset_pwi_efd.json` | Dataset settings (filled in for PWI-EFD; replace the `REPLACE_` values before use) |
| `config/authors_pwi_efd.json` | Author list (filled in for PWI-EFD) |
| `config/authors_instrument_example.json` | Blank author list to start from |
| `config/README.md`, `config/README_ja.md` | The items of the config files, and where each value goes in the labels (English, Japanese) |

For how to write the config files, see [config/README.md](config/README.md).

## Preparation

### Installing miopds_common

The shell scripts call miopds_common as `python -m miopds_common SUBCOMMAND`.
Install miopds_common into its own venv (e.g. `~/mio_pds_validate`). For how
to create the venv and install the package, see "Installation" in
[../README.md](../README.md).

### Choosing the Python on each server

The name of the Python command (`python3` or `python`) and the location of the
venv differ between servers. So the scripts use the Python given in the
environment variable `PYTHON` (`python3` if it is not set). On each server,
give the Python that has miopds_common installed in one of these ways.

| How you run the scripts | How to give the Python |
|---|---|
| By hand | Activate the venv (`source ~/mio_pds_validate/bin/activate`), or run `export PYTHON=~/mio_pds_validate/bin/python` |
| Only once | Write it before the command, as in `PYTHON=~/mio_pds_validate/bin/python ./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi` |
| By cron | Write `PYTHON=$HOME/mio_pds_validate/bin/python` in the crontab line. This is always needed: cron does not activate the venv, and its PATH is minimal |
| Fixed in the instrument repository | In the copied scripts, replace `python3` in `PYTHON="${PYTHON:-python3}"` with the absolute path of the Python on that server |

An example of a crontab line (the paths are examples; change them for the
server):

```bash
0 3 * * * PYTHON=$HOME/mio_pds_validate/bin/python $HOME/instrument_repo/pds/scripts/cron_mk_cdf_to_pds.sh $HOME/pds4/bc_mmo_pwi >> $HOME/pds_chk_log/cron.log 2>&1
```

To check that the Python you gave has miopds_common installed, run:

```bash
"$PYTHON" -c 'import miopds_common; print(miopds_common.__file__)'
```

If it does not, the scripts stop with
`ERROR: miopds_common is not installed for python3` (`python3` is replaced by
the Python you gave).

### Installing PDS Validate 4.2.0

PDS Validate is a Java validation tool distributed by NASA PDS. The packages
are on [GitHub Releases](https://github.com/NASA-PDS/validate/releases), and
its usage is in the [official documentation](https://nasa-pds.github.io/validate/).
The steps below assume that the package `validate-4.2.0-bin.tar.gz` has been
downloaded to `~/Downloads/`.

1. Check that Java is installed.

   ```bash
   java -version
   ```

2. Create the directory to extract into (`mkdir -p` does nothing if the
   directory already exists).

   ```bash
   mkdir -p ~/local/pds
   ```

3. Extract the package (`-C` gives the directory to extract into). This
   creates `~/local/pds/validate-4.2.0/`.

   ```bash
   tar -xzf ~/Downloads/validate-4.2.0-bin.tar.gz -C ~/local/pds
   ```

   To use the ZIP package (`validate-4.2.0-bin.zip`) instead, extract it with
   this command:

   ```bash
   unzip ~/Downloads/validate-4.2.0-bin.zip -d ~/local/pds
   ```

4. Check that it starts.

   ```bash
   ~/local/pds/validate-4.2.0/bin/validate --help
   ```

If you extracted it somewhere else, give that location in the environment
variable `VALIDATE_BIN`. For the Java version needed, see the release notes of
the package.

### XML Catalog

Prepare the XML Catalog (`pds4-validate-catalog.xml`) that resolves the PSA
and BepiColombo dictionaries, and give its absolute path in the environment
variable `VALIDATE_CATALOG`; this is recommended. If the file is not found,
the scripts print a warning and continue the validation without the catalog.

### Settings the current scripts need

With the layout of the quick start, the current scripts do not work unless you
set the following environment variables. This is a bug, to be fixed in
[Issue #7](https://github.com/ergsc-devel/miopds_common/issues/7).

| Environment variable | Value (example) | Used by | Without it |
|---|---|---|---|
| `TIMELINE` | `~/pds_config/mission_timeline.json` | Observational labels | Stops with `TIMELINE: unbound variable` |
| `MISSION_TIMELINE_FILE` | `~/pds_config/mission_timeline.json` | Collection | Stops, because `config/mission_timeline.json` does not exist |
| `ARCHIVE_ROOT` | `~/pds4` | Collection | Its default is a server-specific path, so the Collection directory is not found and the script stops |
| `VALIDATE_BIN` | `~/local/pds/validate-4.2.0/bin/validate` | Collection, Bundle | Its default is `~/local/pds/validate/bin/validate`, so the script stops at the validation |

For how to make the timeline (`mission_timeline.json`), see "Make the timeline"
in [../README.md](../README.md).

## Rules common to the scripts

- The scripts look for the templates and config files by paths relative to the
  script (`../templates/`, `../config/`).
- They save the validation reports by a path relative to where you run them
  (`./pds_chk_log/` by default).
- Except for the observational label script, they validate the labels they
  make with `python -m miopds_common validate`.
- They stop at the first failure. However, it is not yet confirmed that PDS
  Validate exits with a non-zero status on validation errors. After the
  validation, read the reports (see "Known issues" in
  [../docs/usage.md](../docs/usage.md)).

All the scripts use these environment variables:

| Environment variable | Meaning | Default |
|---|---|---|
| `PYTHON` | Python that has miopds_common installed | `python3` |
| `VALIDATE_ENABLED` | `0` skips the validation | `1` |
| `VALIDATE_BIN` | PDS Validate executable | Document: `$HOME/local/pds/validate-4.2.0/bin/validate`. Collection and Bundle: `$HOME/local/pds/validate/bin/validate` |
| `VALIDATE_CATALOG` | Path of the XML Catalog (empty: no catalog) | `pds4-validate-catalog.xml` |
| `REPORT_DIR` | Directory for the validation reports | `./pds_chk_log` |
| `REPORT_TIMESTAMP` | Date and time in the report file names | The date and time of the run |

An example that skips the validation:

```bash
VALIDATE_ENABLED=0 ./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

## Scripts

The Bundle label is made from the Collection labels, so run the scripts in
this order:

1. Observational labels (`make_pds_label_for_mmo_cdf_data.sh`)
2. Data Collection (`create_psa_collection_jinja.sh`)
3. Document (`create_psa_document_jinja.sh`; only when the Bundle includes
   Documents)
4. Bundle (`create_psa_bundle_jinja.sh`)

`cron_mk_cdf_to_pds.sh` runs these four in order.

### Observational labels: `make_pds_label_for_mmo_cdf_data.sh`

Makes one observational label from one CDF file. This script does not
validate.

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh CDF_FILE TEMPLATE_DIR TEMPLATE_NAME OUTPUT_DIR [OPTIONS...]
```

| Argument | Meaning |
|---|---|
| `CDF_FILE` | CDF file |
| `TEMPLATE_DIR` | Template directory |
| `TEMPLATE_NAME` | Template name. `""` means `mmo_cdf_label_template_multi_dataset.xml.j2` |
| `OUTPUT_DIR` | Output directory |
| `OPTIONS` | The arguments from the fifth on are passed to `python -m miopds_common cdf2pdslabel` as options |

| Environment variable | Meaning | Default |
|---|---|---|
| `TIMELINE` | Timeline file (required for now; see "Settings the current scripts need" above) | None |
| `MISSION_CONFIG` | Mission config file | `config/mission.json` |
| `DATASET_CONFIG` | Dataset config file (the instrument and author config files are read from the paths written in it) | `config/dataset_pwi_efd.json` |

The output is `OUTPUT_DIR/CDF file name.lblx` (the CDF file name with `.cdf`
changed to `.lblx`). The mission phase is that of the period in the timeline
that contains the observation start time. `--mission-phase-name` and
`--mission-phase-id` given as options take priority over the timeline. To see
the options, run `python -m miopds_common cdf2pdslabel --help`.

An example:

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates "" \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231
```

The sample `dataset_pwi_efd.json` is rejected until its `REPLACE_` values are
replaced.

### Collection: `create_psa_collection_jinja.sh`

Makes the label and inventory of a data Collection, and validates the
Collection label.

```bash
./pds/scripts/create_psa_collection_jinja.sh [COLLECTION_NAME]
```

`COLLECTION_NAME` is the name of the Collection (default
`data_calibrated_efd`). Only letters, digits, `_` and `-` can be used.

| Environment variable | Meaning | Default |
|---|---|---|
| `ARCHIVE_ROOT` | Location of the bundle directory (required for now) | A server-specific path |
| `BUNDLE_NAME` | Bundle name | `bc_mmo_pwi` |
| `COLLECTION_DIR` | Collection directory | `$ARCHIVE_ROOT/$BUNDLE_NAME/$COLLECTION_NAME` |
| `LABEL_DIR` | Directory searched for observational labels (subdirectories included) | `$COLLECTION_DIR` |
| `COLLECTION_LID` | Collection LID | `urn:jaxa:darts:$BUNDLE_NAME:$COLLECTION_NAME` |
| `OUTPUT_BASE` | Output file name without extension | `$COLLECTION_NAME` |
| `TEMPLATE_FILE` | Template | `templates/collection_template.xml.j2` |
| `MISSION_CONFIG` | Mission config file | `config/mission.json` |
| `DATASET_CONFIG` | Dataset config file | `config/dataset_pwi_efd.json` |
| `MISSION_TIMELINE_FILE` | Timeline file (required for now; the script only checks that it is valid JSON and does not use it for the Collection) | `config/mission_timeline.json` |
| `PUBLICATION_YEAR` | Publication year | `2027` |
| `VERSION_ID` | Collection version | `1.0` |
| `VALIDATE_REPORT` | File for what the validation printed | `$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_validate_report.txt` |
| `SKIP_REPORT` | File listing the labels left out of the inventory | `$REPORT_DIR/${REPORT_TIMESTAMP}_${OUTPUT_BASE}_skipped_missing_cdf.txt` |

The outputs are `OUTPUT_BASE.lblx` (label) and `OUTPUT_BASE.csv` (inventory)
in `COLLECTION_DIR`. Only the observational labels whose CDF files exist enter
the inventory. For a label whose CDF file is not found, the script prints a
warning and saves the list of such labels in `SKIP_REPORT`. This list is not
written in the Collection directory, so that no file without a label is placed
in the archive. The Collection label made before is in `LABEL_DIR`, but it
does not enter the inventory.

The title and description of the Collection are read from `collection` in
`DATASET_CONFIG`, and the Information Model version from `MISSION_CONFIG`.

On macOS, this script stops with `find: -printf: unknown primary or operator`
(Issue #7). On macOS, use the Python command of B in the quick start of
[../README.md](../README.md).

### Document: `create_psa_document_jinja.sh`

Makes the Document label and the Document Collection (label and inventory)
from a PDF, and validates the two labels.

```bash
./pds/scripts/create_psa_document_jinja.sh [DOCUMENT_DIR]
```

`DOCUMENT_DIR` is the directory of the PDF (default `bc_mmo_pwi/document`).

| Environment variable | Meaning | Default |
|---|---|---|
| `PDF_FILE` | PDF name (in `DOCUMENT_DIR`) | `bc_mmo_pwi_data_user_guide.pdf` |
| `DOCUMENT_LID` | Document LID | `urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide` |
| `COLLECTION_LID` | Document Collection LID | `urn:jaxa:darts:bc_mmo_pwi:document` |
| `VERSION_ID` | Version | `1.0` |
| `TITLE` | Document title | The title of the PWI data user guide |
| `DESCRIPTION` | Document description | A description of the PWI data user guide |
| `PUBLICATION_YEAR` | Publication year | `2027` |
| `PUBLICATION_DATE` | Publication date | `2027` |
| `MODIFICATION_DATE` | Modification date (`YYYY-MM-DD`) | The day of the run (UTC) |
| `DOCUMENT_MODIFICATION_DESCRIPTION` | Description of the change of the Document label | A sentence saying that it is the first version |
| `COLLECTION_MODIFICATION_DESCRIPTION` | Description of the change of the Document Collection | A sentence saying that it is the first version |
| `DOCUMENT_OUTPUT` | Document label name | `bc_mmo_pwi_data_user_guide.lblx` |
| `COLLECTION_OUTPUT` | Document Collection label name (`.lblx`) | `collection_bc_mmo_pwi_document.lblx` |
| `INVENTORY_OUTPUT` | Inventory name (must be the `COLLECTION_OUTPUT` name with `.lblx` changed to `.csv`) | `collection_bc_mmo_pwi_document.csv` |
| `DOCUMENT_TEMPLATE` | Document template | `templates/document_template.xml.j2` |
| `COLLECTION_TEMPLATE` | Document Collection template | `templates/document_collection_template.xml.j2` |
| `MISSION_CONFIG` | Mission config file | `config/mission.json` |
| `INSTRUMENT_CONFIG` | Instrument config file | `config/instrument_pwi.json` |
| `DOCUMENT_REPORT` | File for the validation of the Document label | `$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_validate_report.txt` |
| `COLLECTION_REPORT` | File for the validation of the Document Collection label | `$REPORT_DIR/${REPORT_TIMESTAMP}_bc_mmo_pwi_document_collection_validate_report.txt` |

The outputs are three files in `DOCUMENT_DIR`: the Document label, the
Document Collection label and the inventory. The members of the Document
Collection are all the Product_Document labels (`.lblx` and `.xml`) in
`DOCUMENT_DIR` whose document files exist. A label without its document file
is reported as a warning and left out. The title and description of the
Document Collection and the instrument name are read from `INSTRUMENT_CONFIG`,
and the mission name and the Information Model version from `MISSION_CONFIG`.

An example:

```bash
./pds/scripts/create_psa_document_jinja.sh ~/pds4/bc_mmo_pwi/document
```

### Bundle: `create_psa_bundle_jinja.sh`

Collects the Collection labels under the bundle directory, makes the Bundle
label, and validates the whole Bundle.

```bash
./pds/scripts/create_psa_bundle_jinja.sh [BUNDLE_DIR]
```

`BUNDLE_DIR` is the bundle directory (default `bc_mmo_pwi`).

| Environment variable | Meaning | Default |
|---|---|---|
| `BUNDLE_NAME` | Bundle name | The last part of `BUNDLE_DIR` (e.g. `bc_mmo_pwi`) |
| `BUNDLE_LID` | Bundle LID | `urn:jaxa:darts:$BUNDLE_NAME` |
| `BUNDLE_VID` | Bundle version | `1.0` |
| `PUBLICATION_YEAR` | Publication year | `2027` |
| `MODIFICATION_DATE` | Modification date (`YYYY-MM-DD`) | The day of the run (UTC) |
| `OUTPUT_FILE` | Bundle label name | `$BUNDLE_NAME.lblx` |
| `TEMPLATE_FILE` | Template | `templates/bundle_template.xml.j2` |
| `MISSION_CONFIG` | Mission config file | `config/mission.json` |
| `INSTRUMENT_CONFIG` | Instrument config file | `config/instrument_pwi.json` |
| `BUNDLE_LABEL_EXTENSION` | Extension of the files that the validation treats as labels (empty: `xml`, the default of PDS Validate) | `lblx` |
| `VALIDATE_REPORT` | File for PDS Validate's own report (`--report-file`) | `$REPORT_DIR/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_report.txt` |
| `VALIDATE_LOG` | File for what the validation printed | `$REPORT_DIR/${REPORT_TIMESTAMP}_${BUNDLE_NAME}_bundle_validate_log.txt` |

The output is `BUNDLE_DIR/OUTPUT_FILE` (e.g. `~/pds4/bc_mmo_pwi/bc_mmo_pwi.lblx`).
Only the Collection labels with the extension `.lblx` under `BUNDLE_DIR`
become members of the Bundle. The title and description of the Bundle are read
from `bundle` in `INSTRUMENT_CONFIG`, and the Information Model version from
`MISSION_CONFIG`. The Bundle label has no author list. The validation runs on
the whole Bundle with `--rule pds4.bundle`.

An example:

```bash
./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

### Run everything and rebuild only what changed: `cron_mk_cdf_to_pds.sh`

Makes the observational labels, the Collection, the Document and the Bundle in
order, and rebuilds only the products whose inputs have changed. When it runs
regularly, for example by cron, changes to the CDF files and the settings are
carried over to the labels, the Collection and the Bundle.

```bash
./pds/scripts/cron_mk_cdf_to_pds.sh [all] [BUNDLE_DIR]
```

| Argument | Meaning |
|---|---|
| `all` | Rebuild all products (`--all` also works) |
| `BUNDLE_DIR` | Bundle directory (default `bc_mmo_pwi`) |

The current script assumes this layout:

```text
BUNDLE_DIR/data_calibrated_efd/science/**/*.cdf   data (labels are written in the same directory as the CDF)
BUNDLE_DIR/document/*.pdf                         documents (the Document step is skipped if absent)
```

So with the layout of the quick start (directories per phase and per year
under the Collection), it stops with `ERROR: directory not found: .../science`
(Issue #7).

A product is rebuilt when its output does not exist, or when one of these
inputs is newer than the output:

| Output | Inputs |
|---|---|
| Observational label (per CDF) | The CDF file, the dataset config file |
| Collection | Files and directories under `science/` (including added and removed ones) |
| Document and Document Collection | The PDF (`PDF_FILE`) |
| Bundle | The label of each Collection |
| Every product | `templates/`, `config/`, `scripts/` and the Python code of miopds_common |

Editing a template, a config file or a script rebuilds every product. The
script starts Python once per CDF file for the observational labels, so it
takes time when many CDF files are rebuilt.

Edit these two places in the script for the instrument:

| Place to edit | What to write |
|---|---|
| The `set_label_args` function | Extra options passed to `cdf2pdslabel` for each CDF file (mission phase, internal reference, ...) |
| The `make_data_collection` lines | One line per data Collection, with its name and dataset config file. To add a Collection, add a line |

| Environment variable | Meaning | Default |
|---|---|---|
| `BUNDLE_NAME` | Bundle name (used in the lock name and the Bundle label name) | The last part of `BUNDLE_DIR` |
| `PDF_FILE` | Name of the Document PDF | `bc_mmo_pwi_data_user_guide.pdf` |
| `DOCUMENT_OUTPUT` | Document label name | `bc_mmo_pwi_data_user_guide.lblx` |
| `COLLECTION_OUTPUT` | Document Collection label name | `collection_bc_mmo_pwi_document.lblx` |
| `OUTPUT_FILE` | Bundle label name | The last part of `BUNDLE_DIR` + `.lblx` |
| `DATASET_CONFIG` | Dataset config file of the data Collection | `config/dataset_pwi_efd.json` |
| `TEMPLATES_DIR` | Template directory | `templates/` |
| `CONFIG_DIR` | Config file directory | `config/` |
| `LOCK_DIR` | Location of the lock | `$TMPDIR/miopds_cron_mk_cdf_to_pds_${BUNDLE_NAME}.lock` |

The script runs by these rules:

- Only one run at a time is allowed for the same bundle (the script uses a
  lock). If `TMPDIR` differs between cron and runs by hand, give a fixed place
  in `LOCK_DIR`. If a lock is left after an abnormal end, check that no other
  run is active, and then remove the lock directory with `rmdir`.
- All the reports of one run are saved in the same `REPORT_DIR`, with the same
  date and time (`REPORT_TIMESTAMP`) in their names.
- A label whose CDF file is gone is not removed; the script only prints a
  warning (the label is left out of the Collection inventory).
- Each instrument's pipeline makes the L2 CDF files and copies them into the
  data directories before this script runs.

## Related documents

| Document | Contents |
|---|---|
| [../README.md](../README.md) | Installation, and the quick start that runs everything from the beginning |
| [../docs/usage.md](../docs/usage.md) | Subcommands and options, Python usage, the `validate` subcommand, known issues |
| [config/README.md](config/README.md) | The items of the config files, and where each value goes in the labels |
