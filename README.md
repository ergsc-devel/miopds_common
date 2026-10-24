# miopds_common

[日本語](README_ja.md)

## Overview

miopds_common is a Python package that generates the PSA/PDS4 archive from
BepiColombo/Mio (MMO) observation data (CDF). It creates the observational
labels (one `.lblx` per CDF file), the Collection labels and inventories, the
Document labels and the Bundle label, and validates them with NASA PDS
Validate. It is meant for the archive staff of each Mio instrument.

The repository has two parts. `miopds_common/` is the Python package installed
by pip. `examples/` holds sample shell scripts, Jinja2 templates and config
files (JSON). pip does not install `examples/`, so copy it into each instrument
repository.

## Installation

Install miopds_common into its own venv (Python virtual environment). A
separate venv keeps the versions of cdflib, Jinja2 and numpy used by
miopds_common apart from the packages installed for other work.

### 1. Check the Python version

miopds_common needs Python 3.11 or later.

```bash
python3 --version
```

If it shows `Python 3.11` or later, you can use it. If it is older, install
Python 3.11 or later (for example with miniforge), or use uv in step 3. When uv
cannot find the requested Python version, it downloads that version to create
the venv.

### 2. Get the source

This example puts the source under the home directory (`~`).

```bash
cd ~
```

```bash
git clone https://github.com/ergsc-devel/miopds_common.git
```

This creates `~/miopds_common`.

### 3. Create a venv and install

There are two ways to create the venv; use one of them. The examples below put
the venv at `~/mio_pds_validate` (the same name as in `examples/README.md`).

With the standard venv of Python, run these three commands in order:

```bash
python3 -m venv ~/mio_pds_validate
```

```bash
source ~/mio_pds_validate/bin/activate
```

```bash
pip install ~/miopds_common
```

With uv, run these three commands in order. A venv created by uv has no pip, so
give the Python of the venv to `--python` of `uv pip install`.

```bash
uv venv --python 3.13 ~/mio_pds_validate
```

```bash
source ~/mio_pds_validate/bin/activate
```

```bash
uv pip install --python ~/mio_pds_validate/bin/python ~/miopds_common
```

`source ~/mio_pds_validate/bin/activate` activates the venv. After it, `python`
and `pip` in that terminal are the ones in the venv. Run it again whenever you
open a new terminal. cron does not activate the venv; to give the Python for
cron, see "Choosing the Python on each server" in
[examples/README.md](examples/README.md).

### 4. Check the installation

```bash
python -c 'import miopds_common; print(miopds_common.__file__)'
```

If it prints a path inside the venv, such as
`~/mio_pds_validate/lib/python3.13/site-packages/miopds_common/__init__.py`, the
package is installed. Do not run this command inside `~/miopds_common`. There,
Python loads the local source instead of the installed package, so it prints a
path even when the package is not installed.

To use the package while editing its code, install it with `pip install -e`.
See "Development" in [docs/usage.md](docs/usage.md).

PDS Validate (the Java tool for validation) is needed only for validation. For
its installation, see "Installing PDS Validate 4.2.0" in
[examples/README.md](examples/README.md).

## Quick start

### Preparation

Run the commands at the top of the instrument repository. The instrument
repository holds a copy of `examples/` of miopds_common, named `pds/`. The data
(the bundle directory) is kept outside the repository. The examples below put
the bundle at `~/pds4/bc_mmo_pwi/` and use the sample values for PWI-EFD
(bundle `bc_mmo_pwi`, Collection `data_calibrated_efd`). For other
instruments, replace the names and locations with those of the instrument.

```text
instrument_repo/                          # instrument repository (example)
└── pds/                                  # copy of examples/ of miopds_common
    ├── scripts/
    ├── templates/
    └── config/

~/pds4/
└── bc_mmo_pwi/                           # bundle directory
    └── data_calibrated_efd/              # Collection directory
        ├── cruise/                       # data of Cruise
        │   └── sc/
        │       └── YYYY0101_YYYY1231/    # directory per year (CDF files)
        └── mercury_science_orbit/        # data of Mercury Science Phase
            └── sc/
                └── YYYY0101_YYYY1231/
```

The observational labels are written in the same directory as the CDF files.

1. Copy `examples/` into the instrument repository as `pds/`. Run this while
   `pds/` does not exist yet (if it exists, `pds/examples/` is created
   instead).

   ```bash
   cp -R ~/miopds_common/examples pds
   ```

2. Replace the three values under `collection` in
   `pds/config/dataset_pwi_efd.json` (`title`, `citation_description` and
   `collection_description`). The sample has placeholder values that start with
   `REPLACE_`. If one is left, a command given this file with
   `--dataset-config` stops with this error:

   ```text
   ERROR: .../pds/config/dataset_pwi_efd.json.collection.title: placeholder 'REPLACE_COLLECTION_TITLE' must be replaced
   ```

   For other instruments, also write `instrument_*.json`, `dataset_*.json` and
   `authors_*.json` for the instrument. The meaning of each item is in
   [examples/config/README.md](examples/config/README.md).

3. Activate the venv.

   ```bash
   source ~/mio_pds_validate/bin/activate
   ```

The examples below split long commands over several lines with `\`. A `\` at
the end of a line means that the command continues on the next line.

### Make the timeline

To decide the mission phase of the observational labels with a timeline, make
the timeline file (`mission_timeline.json`) before A. If you do not use a
timeline, skip this section.

The timeline is made from the team's mission phase table
(`mission_phases.tab`). The periods of the phases are not public, so keep the
table and the timeline outside the repository (`~/pds_config/` in this
example).

1. Create the directory (`mkdir -p` does nothing if the directory already
   exists).

   ```bash
   mkdir -p ~/pds_config
   ```

2. Get `mission_phases.tab` from the team and put it in `~/pds_config/`.

3. Convert the table into `mission_timeline.json` with `tab2timeline`.

   ```bash
   python -m miopds_common tab2timeline ~/pds_config/mission_phases.tab ~/pds_config/mission_timeline.json
   ```

   The arguments are the table to convert and the timeline to write, in this
   order. If the last phase in the table is not `msp`, its end is unknown and
   the command fails. In that case, give the end time with `--end`. For the
   table format and the conversion rules, see "Converting from .tab" in
   [examples/config/README.md](examples/config/README.md).

When the table is updated, convert it again. If the content has not changed,
`mission_timeline.json` is not rewritten.

### Preparing to use the shell scripts

Each step from A to D can also be run with the shell scripts in
`pds/scripts/`, not only with the Python commands. The shell scripts read the
templates and config files from `pds/templates/` and `pds/config/`, and save
the validation reports in `pds_chk_log/` in the repository. If you use only
the Python commands, skip this section.

The current scripts do not work with this layout unless you set the following
four environment variables. This is a bug, to be fixed in
[Issue #7](https://github.com/ergsc-devel/miopds_common/issues/7).

| Environment variable | Value | Used by |
|---|---|---|
| `TIMELINE` | Timeline file | Observational labels (A) |
| `MISSION_TIMELINE_FILE` | Timeline file | Collection (B) |
| `ARCHIVE_ROOT` | Location of the bundle directory | Collection (B) |
| `VALIDATE_BIN` | PDS Validate executable | Collection (B), Bundle (C) |

Even if you do not use a timeline, the current scripts stop without the
timeline file. Make the timeline first in "Make the timeline" above.

`export` sets an environment variable and passes it to the commands run later
in that terminal. Run these four commands in order. Run them again whenever
you open a new terminal.

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

Except for the observational label script, the shell scripts validate the
labels they make with PDS Validate. If PDS Validate is not installed yet, skip
the validation with this command:

```bash
export VALIDATE_ENABLED=0
```

### A. Make observational labels only

Make one observational label from one CDF file.

#### With the Python command

```bash
python -m miopds_common cdf2pdslabel \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates/mmo_cdf_label_template_multi_dataset.xml.j2 \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231 \
  --mission-config pds/config/mission.json \
  --dataset-config pds/config/dataset_pwi_efd.json
```

The arguments are the CDF file, the template and the output directory, in this
order. The label name is the CDF file name with `.cdf` changed to `.lblx`
(`bc_mmo_pwi-efd_l2_example_20270101_v01.lblx` in this example). The CDF file
name must contain an 8-digit date between `_` characters, such as
`_20270101_`.

To process all the CDF files of the Collection, repeat the command with `for`.

```bash
for cdf in ~/pds4/bc_mmo_pwi/data_calibrated_efd/*/sc/*/*.cdf; do
  python -m miopds_common cdf2pdslabel "$cdf" \
    pds/templates/mmo_cdf_label_template_multi_dataset.xml.j2 \
    "$(dirname "$cdf")" \
    --mission-config pds/config/mission.json \
    --dataset-config pds/config/dataset_pwi_efd.json
done
```

`*/sc/*/*.cdf` matches the CDF files in the directories of every phase and
every year. `"$(dirname "$cdf")"` is the directory of that CDF file, so each
label is written beside its CDF file.

If you do not give the mission phase, the default in `mission.json` (Mercury
Science Phase, `msp`) is written to the labels. To use the timeline made in
"Make the timeline" above, add `--timeline ~/pds_config/mission_timeline.json`.
The phase of the period that contains the observation start time is then
written to the labels. Instead of a timeline, you can also give both
`--mission-phase-name` and `--mission-phase-id`. See "Mission phase timeline"
in [docs/usage.md](docs/usage.md).

#### With the shell script

`make_pds_label_for_mmo_cdf_data.sh` makes one observational label from one
CDF file.

```bash
./pds/scripts/make_pds_label_for_mmo_cdf_data.sh \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231/bc_mmo_pwi-efd_l2_example_20270101_v01.cdf \
  pds/templates "" \
  ~/pds4/bc_mmo_pwi/data_calibrated_efd/mercury_science_orbit/sc/20270101_20271231
```

| Order | Argument | Value in this example |
|---|---|---|
| 1 | CDF file | `~/pds4/.../bc_mmo_pwi-efd_l2_example_20270101_v01.cdf` |
| 2 | Template directory | `pds/templates` |
| 3 | Template name (`""` means `mmo_cdf_label_template_multi_dataset.xml.j2`) | `""` |
| 4 | Output directory | `~/pds4/.../20270101_20271231` |

Arguments after the fourth are passed to `cdf2pdslabel` as options (e.g.
`--mission-phase-name Cruise --mission-phase-id cruise`). The script reads the
config files `pds/config/mission.json` and `pds/config/dataset_pwi_efd.json`
(change them with the environment variables `MISSION_CONFIG` and
`DATASET_CONFIG`). The mission phase comes from the timeline in the
environment variable `TIMELINE`. This script does not validate.

To process all the CDF files of the Collection, repeat it with `for`, as with
the Python command.

```bash
for cdf in ~/pds4/bc_mmo_pwi/data_calibrated_efd/*/sc/*/*.cdf; do
  ./pds/scripts/make_pds_label_for_mmo_cdf_data.sh "$cdf" pds/templates "" "$(dirname "$cdf")"
done
```

### B. Make labels up to the Collection

Collect the observational labels made in A, and make the label and inventory
of the data Collection.

#### With the Python command

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

| Order | Argument | Value in this example |
|---|---|---|
| 1 | Directory searched for observational labels (subdirectories included) | `~/pds4/bc_mmo_pwi/data_calibrated_efd` |
| 2 | Output directory | `~/pds4/bc_mmo_pwi/data_calibrated_efd` |
| 3 | Template | `pds/templates/collection_template.xml.j2` |
| 4 | Collection LID | `urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd` |
| 5 | Output file name without extension | `data_calibrated_efd` |

With the Collection directory as the first argument, the command collects the
observational labels from the directories of every phase and year. The
Collection label made before is in the same directory, but it does not enter
the inventory. The outputs are `data_calibrated_efd.lblx` (label) and
`data_calibrated_efd.csv` (inventory) in `~/pds4/bc_mmo_pwi/data_calibrated_efd/`.
An observational label whose CDF file is missing is reported as a warning and
left out of the inventory.

#### With the shell script

Give the Collection name to `create_psa_collection_jinja.sh`. It makes the
label and inventory of the Collection, and validates the Collection label.

```bash
./pds/scripts/create_psa_collection_jinja.sh data_calibrated_efd
```

The Collection directory is `$ARCHIVE_ROOT/bc_mmo_pwi/data_calibrated_efd`
(`~/pds4/bc_mmo_pwi/data_calibrated_efd` in this example). Change the bundle
name with the environment variable `BUNDLE_NAME` (default `bc_mmo_pwi`). The
validation report is saved in `pds_chk_log/` with the date and time in its
name.

On macOS, this script stops with
`find: -printf: unknown primary or operator` (Issue #7). On macOS, use the
Python command above. The `find` of Linux has this feature, so the script
should not stop there, but this is not checked yet.

### C. Make labels up to the Bundle

After making the Collection in B, collect the Collection labels under the
bundle directory and make the Bundle label.

#### With the Python command

```bash
python -m miopds_common collections2bundle ~/pds4/bc_mmo_pwi \
  --template pds/templates/bundle_template.xml.j2 \
  --bundle-lid urn:jaxa:darts:bc_mmo_pwi \
  --mission-config pds/config/mission.json \
  --instrument-config pds/config/instrument_pwi.json \
  --publication-year 2027
```

The output is `~/pds4/bc_mmo_pwi/bc_mmo_pwi.lblx`. To include Documents (PDF files) in
the Bundle, make the Document labels and the Document Collection with
`pdf2document` before making the Bundle. See "pdf2document: Document and
Document Collection" in [docs/usage.md](docs/usage.md).

#### With the shell scripts

To include Documents in the Bundle, run `create_psa_document_jinja.sh` before
making the Bundle. From the PDF in `~/pds4/bc_mmo_pwi/document/` (by default
`bc_mmo_pwi_data_user_guide.pdf`), it makes the Document label and the
Document Collection, and validates them.

```bash
./pds/scripts/create_psa_document_jinja.sh ~/pds4/bc_mmo_pwi/document
```

Change the PDF name and the Document title with environment variables (see
"Document" in [examples/README.md](examples/README.md)).

Then give the bundle directory to `create_psa_bundle_jinja.sh` to make the
Bundle label.

```bash
./pds/scripts/create_psa_bundle_jinja.sh ~/pds4/bc_mmo_pwi
```

After making the Bundle label, this script validates the whole Bundle with PDS
Validate (it also does the validation of D). The validation reports are saved
in `pds_chk_log/` with the date and time in their names.

### D. Validate

Validate the whole Bundle with PDS Validate, and save what it prints to
`pds_chk_log/bundle_screen.log` in the repository. If you used the shell
scripts, `create_psa_bundle_jinja.sh` in C has already done this validation,
so this step is not needed.

```bash
python -m miopds_common validate ~/pds4/bc_mmo_pwi \
  --report pds_chk_log/bundle_screen.log \
  --validate-bin ~/local/pds/validate-4.2.0/bin/validate \
  --rule pds4.bundle \
  --label-extension lblx
```

Give the PDS Validate executable to `--validate-bin` (the example is the
location used in the installation steps of `examples/README.md`). After the
validation, read the report whatever the exit status is. The reason is in
"Known issues" in [docs/usage.md](docs/usage.md).

### Run everything

`pds/scripts/cron_mk_cdf_to_pds.sh` (`examples/scripts/cron_mk_cdf_to_pds.sh`
in miopds_common) runs A to D and the Document step in
order, and rebuilds only the products whose inputs have changed. It is meant to
be run regularly by cron. See [examples/README.md](examples/README.md).

However, the current script looks for `science/` under the Collection, so it
stops at the first step with this layout (Issue #7).

## Documentation

| Document | Contents |
|---|---|
| [docs/usage.md](docs/usage.md) | Package guide: subcommands and options, Python usage, config files, validation, development |
| [examples/README.md](examples/README.md) | Shell scripts: arguments, environment variables and outputs |
| [examples/config/README.md](examples/config/README.md) | Config files and where each value goes in the labels |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Git branches and their policies |
