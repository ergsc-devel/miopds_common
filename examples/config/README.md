# Sample config files (examples/config)

[日本語](README_ja.md)

`examples/config/` holds sample config files (JSON) used to make PDS4 labels.
Copy them with `examples/` into the instrument repository (e.g. `pds/config/`),
and adapt them to the instrument and dataset.

This document explains the meaning of each item in the config files, and which
element of which label each value goes to.

## Files and the subcommands that read them

The config files are split into four levels, following the structure of the
PDS4 archive.

| File | Level | PDS4 unit | Read by (`python -m miopds_common ...`) |
|---|---|---|---|
| `mission.json` | Mission (shared by Mio/BepiColombo) | — | All subcommands |
| `instrument_pwi.json` | Instrument | Bundle (e.g. `bc_mmo_pwi`) | `collections2bundle`, `pdf2document`. `cdf2pdslabel` reads it through `instrument_file` in `dataset_*.json` |
| `dataset_pwi_efd.json` | Dataset | Data Collection (e.g. `data_calibrated_efd`) | `cdf2pdslabel`, `labels2collection` |
| `authors_pwi_efd.json` | Author list | `List_Author` of the observational labels | `cdf2pdslabel` (through `authors_file` in `dataset_*.json`) |

`pdf2pdslabel` reads only `mission.json`. The values of the Document itself
(title, PDF name and so on) are given as command arguments or as environment
variables of the shell scripts.

The timeline (`mission_timeline.json`), which decides the mission phase and
target from the observation date, is not kept in this repository, because the
periods of the phases are not public. For how to make it, see "How the mission
phase and target are decided" below.

## Common rules

- JSON allows no comments. The meaning of each item is described in this
  document.
- A comma after the last element is an error (e.g. `["a", "b",]` is not
  allowed).
- A relative path is resolved from the directory of the JSON file, not from
  the directory where you run the command.
- A value that starts with `REPLACE_` is a placeholder that you must replace.
  If one is left, the file is rejected when it is read, even if the command
  does not use that item.

  ```text
  ERROR: .../dataset_pwi_efd.json.collection.title: placeholder 'REPLACE_COLLECTION_TITLE' must be replaced
  ```

## How to read the tables (label kinds and XML locations)

The tables below show which XML element of which label each JSON item goes
to. There are five kinds of labels:

| Name in the tables | Label (outermost element) | Made by |
|---|---|---|
| Observational | Observational label (`Product_Observational`), one per CDF file | `cdf2pdslabel` |
| Collection | Label of a data Collection (`Product_Collection`) | `labels2collection` |
| Bundle | Bundle label (`Product_Bundle`) | `collections2bundle` |
| Document | Document label (`Product_Document`) | `pdf2pdslabel`, `pdf2document` |
| Document Collection | Label of the document Collection (`Product_Collection`) | `pdf2document` |

- "XML location" is the path from just inside the outermost element.
  `A/B/c` means "`c` in `B` in `A`".
- Elements that start with `psa:` or `msn:` are defined in the PSA dictionary
  or the Mission dictionary (this mark is called a namespace prefix).
- To find where the value of a label element comes from, see "Tracing back
  from the labels" below. It also lists values that come from outside JSON
  (CDF, command arguments).

## mission.json (shared by the mission)

| Item | Label | XML location | Description |
|---|---|---|---|
| `information_model_version` | All | `Identification_Area/information_model_version` | Version of the PDS4 Information Model |
| `investigation.name` / `.type` / `.lid` | Observational, Document Collection | `name` / `type` / `Internal_Reference/lid_reference` of `Investigation_Area`. `Investigation_Area` is in `Observation_Area` in the observational labels, and in `Context_Area` in the Document Collection | The mission (BepiColombo) |
| `instrument_host.name` / `.lid` | Observational | `name` / `Internal_Reference/lid_reference` of `Observation_Area/Observing_System/Observing_System_Component` whose `type` is `Host` | The spacecraft (MMO) |
| `cdf_parsing_standard_id` | Observational | `File_Area_Observational/Header/parsing_standard_id` | Standard for parsing the CDF header |
| `default_mission_phase.name` | Observational | Two places: `Observation_Area/Mission_Area/psa:Mission_Information/psa:Mission_Phase/psa:name` and `Observation_Area/Discipline_Area/msn:Mission_Information/msn:mission_phase_name` | Name of the default mission phase |
| `default_mission_phase.id` | Observational | `Observation_Area/Mission_Area/psa:Mission_Information/psa:Mission_Phase/psa:id` | ID of the default mission phase |
| `default_target.name` / `.type` / `.lid` | Observational | `name` / `type` / `Internal_Reference/lid_reference` of `Observation_Area/Target_Identification` | Default target |

`default_mission_phase` and `default_target` are used when neither the command
arguments nor the timeline decide the value (see "How the mission phase and
target are decided" below).

## instrument_pwi.json (instrument = Bundle unit)

| Item | Label | XML location | Description |
|---|---|---|---|
| `instrument.name` | Observational, Document Collection | Observational: `name` of `Observation_Area/Observing_System/Observing_System_Component` whose `type` is `Instrument`. Document Collection: `Context_Area/Observing_System/Observing_System_Component/name` | Instrument name |
| `instrument.lid` | Observational | `Internal_Reference/lid_reference` of the observational `Observing_System_Component` above | LID of the instrument context product |
| `bundle.title` | Bundle | `Identification_Area/title` | Bundle title |
| `bundle.description` | Bundle | `Identification_Area/Citation_Information/description` | Bundle description |
| `document_collection.title` | Document Collection | `Identification_Area/title` | Title |
| `document_collection.citation_description` | Document Collection | `Identification_Area/Citation_Information/description` | Description for citation |
| `document_collection.collection_description` | Document Collection | `Collection/description` | Collection description |

The pair of the instrument name and the instrument LID is defined by the rules
of the BepiColombo dictionary (e.g. PWI is
`urn:jaxa:darts:context:instrument:mmo.pwi`).

## dataset_pwi_efd.json (dataset = Data Collection unit)

| Item | Label | XML location | Description |
|---|---|---|---|
| `instrument_file` | — | — | Path to the instrument config file (relative to this file) |
| `authors_file` | — | — | Path to the author list (relative to this file) |
| `purpose` | Observational | `Observation_Area/Primary_Result_Summary/purpose` | Purpose of the data |
| `processing_level` | Observational | `Observation_Area/Primary_Result_Summary/processing_level` | Processing level |
| `science_facets.domains` | Observational | `Observation_Area/Primary_Result_Summary/Science_Facets/domain` | List of domains. Each element of the list becomes one `domain` |
| `science_facets.discipline_name` | Observational | `Observation_Area/Primary_Result_Summary/Science_Facets/discipline_name` | Discipline |
| `science_facets.facet1` / `.facet2` | Observational | `Observation_Area/Primary_Result_Summary/Science_Facets/facet1` / `facet2` | Subdivisions of the discipline. If one does not apply, leave out the item (the element is not written either; an empty string is an error) |
| `cdf.time_variable` | Observational | `Observation_Area/Time_Coordinates/start_date_time` / `stop_date_time` | The variable name does not go into the label. The first and last values of this CDF variable become the start and stop times of the observation |
| `cdf.epoch_variable` | — | — | Does not go into the label. Used to check that it has as many records as the time variable, and for the number of elements on the time axis of the arrays |
| `collection.collection_type` | Collection | `Collection/collection_type` | Collection type |
| `collection.title` | Collection | `Identification_Area/title` | Title |
| `collection.citation_description` | Collection | `Identification_Area/Citation_Information/description` | Description for citation |
| `collection.collection_description` | Collection | `Collection/description` | Collection description |

The values allowed for `purpose`, `processing_level` and the items of
Science_Facets are defined by the PDS4 standards. PDS Validate finds wrong
values.

This file holds the title and description of the Collection on the
assumption that one Data Collection holds only one kind of dataset. If one
Collection holds several datasets, they cannot be written in this form.

## authors_*.json (author list)

The author list is a list of objects. Each element needs all three items
below, and empty strings are not allowed. The author list goes only into the
observational labels (not into the Collection, Bundle or Document labels).
Each element of the list becomes one `Person`, in the order written.

| Item | Label | XML location | Example |
|---|---|---|---|
| `display_full_name` | Observational | `Identification_Area/Citation_Information/List_Author/Person/display_full_name` | `"Shinbori, A."` |
| `given_name` | Observational | `Identification_Area/Citation_Information/List_Author/Person/given_name` | `"A."` |
| `family_name` | Observational | `Identification_Area/Citation_Information/List_Author/Person/family_name` | `"Shinbori"` |

`authors_instrument_example.json` is a blank list to start from, and
`authors_pwi_efd.json` is a filled-in example.

## Tracing back from the labels

The figures below show where the value of each label element comes from.
"Argument" in the figures is an option of `python -m miopds_common SUBCOMMAND`
(the shell scripts pass it from environment variables or arguments).

`logical_identifier` holds the whole LID, not only the ID part. A LID joins,
after the prefix, the bundle ID, the Collection ID and the product ID, as far
as the level of the product, separated by colons (`:`).

| Product | Form of the LID | Example |
|---|---|---|
| Bundle | `prefix:bundle ID` | `urn:jaxa:darts:bc_mmo_pwi` |
| Collection | `prefix:bundle ID:Collection ID` | `urn:jaxa:darts:bc_mmo_pwi:data_calibrated_efd` |
| Product (observational data, document) | `prefix:bundle ID:Collection ID:product ID` | `urn:jaxa:darts:bc_mmo_pwi:document:bc_mmo_pwi_data_user_guide` |

In the shell scripts, `BUNDLE_NAME` is the bundle ID, and the first argument
of `create_psa_collection_jinja.sh` (`COLLECTION_NAME`) is the Collection ID.
The shell scripts add the prefix `urn:jaxa:darts` to them to make the whole
LID (you can also give the whole LID with `BUNDLE_LID` and `COLLECTION_LID`).

The rules for LIDs are in the PDS4 Data Provider's Handbook 1.22.0. The
allowed characters (lower-case letters, digits, `-`, `.` and `_`; `:` only as
a separator) and the length (up to 255 characters) are in Section 5.1 (p.21),
and how to construct a LID is in Section 5.2 (p.22). The complete rules are in
Section 6D.2 of the Standards Reference, which the Handbook refers to. The
prefix `urn:jaxa:darts` is a JAXA rule and is not in the Handbook (the
Handbook's examples are `urn:nasa:pds` and `urn:esa:psa`).

### Observational label (Product_Observational)

```text
Product_Observational
├─ Identification_Area
│  ├─ logical_identifier .......... CDF attribute PDS_LOGICAL_IDENTIFIER (whole product LID; YYYYMMDD is replaced with the date in the file name)
│  ├─ version_id .................. CDF attribute PDS_VERSION_IDENTIFIER (1.0 if absent)
│  ├─ title ....................... CDF attribute TITLE (if absent, the CDF file name without its extension)
│  ├─ information_model_version ... mission.json: information_model_version
│  ├─ Citation_Information
│  │  ├─ publication_year ......... argument --publication-year (if absent, the year of the CDF modification time)
│  │  ├─ description .............. argument --description (if absent, CDF attribute Logical_source_description, then TITLE)
│  │  └─ List_Author/Person ....... authors_*.json (authors_file in dataset_*.json)
│  └─ Modification_History ........ the day of the run (UTC), and argument --modification-description
├─ Observation_Area
│  ├─ Time_Coordinates ............ first and last values of the CDF variable (dataset_*.json: cdf.time_variable)
│  ├─ Primary_Result_Summary ...... dataset_*.json: purpose, processing_level, science_facets
│  ├─ Investigation_Area .......... mission.json: investigation
│  ├─ Observing_System
│  │  ├─ Component (type Host) ......... mission.json: instrument_host
│  │  └─ Component (type Instrument) ... instrument_*.json: instrument (instrument_file in dataset_*.json)
│  ├─ Target_Identification ....... argument --target-* → targets in the timeline → mission.json: default_target (in this order)
│  ├─ Mission_Area
│  │  ├─ psa:Mission_Information
│  │  │  ├─ psa:spacecraft_clock_start_count / stop_count ... CDF attributes PDS_SCLK_START_COUNT / PDS_SCLK_STOP_COUNT
│  │  │  └─ psa:Mission_Phase ..... argument --mission-phase-* → mission_phases in the timeline → mission.json: default_mission_phase
│  │  └─ psa:Processing_Context ... CDF attributes GENERATION_SOFTWARE, SOFTWARE_VERSION, SOURCE_FILE
│  └─ Discipline_Area/msn:Mission_Information ... name of the mission phase and SCLK (same values as above)
├─ Reference_List ................. argument --internal-reference (written only when given)
└─ File_Area_Observational
   ├─ File ........................ the CDF file itself (name, modification time, size, MD5)
   ├─ Header ...................... argument --header-length, mission.json: cdf_parsing_standard_id
   └─ Array / Table_Binary ........ each CDF variable (name, offset, type, attributes CATDESC, UNITS, FILLVAL, VALIDMIN, VALIDMAX)
```

### Data Collection (Product_Collection)

```text
Product_Collection
├─ Identification_Area
│  ├─ logical_identifier .......... argument (whole Collection LID; the shell scripts make it from urn:jaxa:darts:BUNDLE_NAME:COLLECTION_NAME)
│  ├─ version_id .................. argument --version-id
│  ├─ title ....................... dataset_*.json: collection.title
│  ├─ information_model_version ... mission.json: information_model_version
│  └─ Citation_Information
│     ├─ publication_year ......... argument --publication-year
│     └─ description .............. dataset_*.json: collection.citation_description
├─ Collection
│  ├─ collection_type ............. dataset_*.json: collection.collection_type
│  └─ description ................. dataset_*.json: collection.collection_description
└─ File_Area_Inventory ............ name, size, MD5 and number of rows of the inventory (.csv) made
```

### Bundle (Product_Bundle)

```text
Product_Bundle
├─ Identification_Area
│  ├─ logical_identifier .......... argument --bundle-lid (whole bundle LID; the shell scripts make it from urn:jaxa:darts:BUNDLE_NAME)
│  ├─ version_id .................. argument --version-id
│  ├─ title ....................... instrument_*.json: bundle.title
│  ├─ information_model_version ... mission.json: information_model_version
│  ├─ Citation_Information
│  │  ├─ publication_year ......... argument --publication-year
│  │  └─ description .............. instrument_*.json: bundle.description
│  └─ Modification_History ........ argument --modification-date (if absent, the day of the run), --modification-description
├─ Bundle/bundle_type ............. fixed (Archive)
└─ Bundle_Member_Entry ............ the Collection labels found under the bundle directory (LID and kind)
```

### Document and Document Collection

| Label | Values from JSON | Other values |
|---|---|---|
| Document (`Product_Document`) | mission.json: `information_model_version` | LID, title, description, publication year and date, version, language and PDF file name are all arguments |
| Document Collection (`Product_Collection`) | mission.json: `information_model_version`, `investigation`. instrument_*.json: `instrument.name`, the three items of `document_collection` | LID, version, publication year and modification history are arguments. `collection_type` is fixed (Document) |

## How the mission phase and target are decided

The mission phase and target of an observational label are decided in this
order:

1. Command arguments (`--mission-phase-name`, `--mission-phase-id`,
   `--target-name` and so on)
2. The timeline (`mission_timeline.json`), only when it is given. The values
   of the period that contains the observation start time are used; if the
   start time is in no period, it is an error
3. `default_mission_phase` and `default_target` in `mission.json`

When you use the Python commands without a timeline, give the arguments of
item 1 for data from periods other than Mercury Science Phase (`msp`).
Otherwise the defaults are written to the labels. The current shell scripts do
not work without the timeline file (see "Settings the current scripts need" in
[../README.md](../README.md)).

### Format of mission_timeline.json

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

- The phases and the targets change at different times, so they are in
  separate lists.
- Each period covers "start or later, and before stop". A time exactly on a
  boundary belongs to the later period.
- A product that crosses a period boundary is judged by its observation start
  time.
- Overlapping periods, and a start that is not before its stop, are errors
  when the file is read.
- A date and time without a time zone is taken as UTC.

Each item goes only into the observational labels, at the same places as the
defaults in `mission.json` (`mission_phases[]` means "each element of the
`mission_phases` list").

| Item | Label | XML location |
|---|---|---|
| `mission_phases[].name` | Observational | The same two places as `default_mission_phase.name` |
| `mission_phases[].id` | Observational | The same place as `default_mission_phase.id` |
| `targets[].name` / `.type` / `.lid` | Observational | The same places as `default_target` |
| `start` / `stop` | — | Do not go into the label. Used to find the period that contains the observation start time |

### Where to keep mission_timeline.json and how to use it

The periods of the phases are not public, so keep the real timeline only on
the server, not in git.

1. Make the timeline and put it outside the repository on the server (e.g.
   `~/pds_config/mission_timeline.json`). There are two ways to make it:
   - Convert the team's mission phase table (`.tab`) (see "Converting from
     .tab" below)
   - Write a file in the format above, with the real dates and times
2. To use the timeline, give its path to `--timeline` of the Python commands.
   With the current shell scripts, give it in the environment variables
   `TIMELINE` (observational labels) and `MISSION_TIMELINE_FILE` (Collection)
   (see "Settings the current scripts need" in [../README.md](../README.md)).
   When you run them by cron, write these environment variables in the crontab
   line.

Follow these rules when you write the timeline:

- `.gitignore` excludes files named `mission_timeline.json` and
  `mission_*.tab`. If you put one in the repository by mistake, it is not
  pushed; but a renamed file is not excluded, so keep the files outside the
  repository.
- Cover the whole period of the data without gaps. An observation in no period
  is an error.
- For the `stop` of a phase whose end is not decided, write a date far in the
  future (e.g. `2100-01-01T00:00:00Z`).
- `targets` can be left out. Then the target is `default_target` in
  `mission.json`.

### Converting from .tab (tab2timeline)

Make `mission_timeline.json` from the team's mission phase table (`.tab`; the
dates are not public). In this example, the table `mission_phases.tab` is in
`~/pds_config/`.

```bash
python -m miopds_common tab2timeline ~/pds_config/mission_phases.tab ~/pds_config/mission_timeline.json
```

Each line of the table is the start of one phase. The columns are separated by
commas and aligned with spaces.

```text
# Start Time            ,Mission Phase Acronym ,Mission Phase Name ,Path to folder
YYYY-MM-DDThh:mm:ss.sssZ ,cruise                ,Cruise             ,cruise
```

| Column of the table | Use in `mission_timeline.json` |
|---|---|
| Start Time | `start` of the phase. It is also the `stop` of the previous phase |
| Mission Phase Acronym | `id` |
| Mission Phase Name | `name` |
| Path to folder | Not used |

The conversion follows these rules:

- Lines that start with `#` (header) and empty lines are skipped.
- The `stop` of each phase is the `Start Time` of the next phase. Consecutive
  lines of the same phase are merged into one period.
- The last phase must be `msp`. Its `stop` is `2100-01-01T00:00:00Z` (change
  it with `--end`). A table whose last phase is not `msp` is an error, because
  its end is unknown; give the end time of that phase with `--end` to convert
  it.
- A line whose `Start Time` does not increase, a line without exactly four
  columns, and a line with a wrong date format are errors (the error shows the
  line number).
- Before writing, the same checks as when the timeline is used (overlapping
  periods and so on) are made.
- It is not checked that the acronyms (Mission Phase Acronym) are spelled the
  same as the IDs in the PSA dictionary. After the first conversion, compare
  the acronyms with "Values allowed for the mission phase" below.
- When the table changes, convert it again. `mission_timeline.json` is
  rewritten only when its content changes, so `cron_mk_cdf_to_pds.sh` rebuilds
  the observational labels at the next run. When the content does not change,
  the file is not rewritten (its time stamp does not change either), so
  converting it at every cron run does not rebuild the observational labels
  every time.

### Values allowed for the mission phase

The allowed pairs of name and id are defined by the Schematron of the
BepiColombo mission dictionary published by PSA:

- https://psa.esa.int/psa/bc/v1/PDS4_BC_1M00_2010.sch
  (checked on 2026-10-01 with dictionary version 2.0.1.0. They may change
  when the dictionary is updated, so check them with the dictionary version
  used for delivery)

Examples: `Cruise` / `cruise`, `Mercury Orbit Commissioning Phase` / `mocp`,
`Mercury Science Phase` / `msp`

A value that is not in the list is an error in PDS Validate.
