# miopds_common
Common libraries for generating the PDS archive of BepiColombo/MMO data

Product lists
- filetool
- cdftool
- Bundle related tools
- Collection related tools
- Label related tools
- Document related tools

## Installation

Python 3.11 or later is required.

```bash
pip install /path/to/miopds_common        # or: pip install -e /path/to/miopds_common
```

The tools are run as `python -m miopds_common <subcommand>`; the subcommands are
named after the subpackages (`cdf2pdslabel`, `labels2collection`, `pdf2pdslabel`,
`pdf2document`, `collections2bundle`) plus `validate`:

```bash
python -m miopds_common --help
```

The same tools are also installed as the commands `miopds-label`,
`miopds-collection`, `miopds-document`, `miopds-document-set`, `miopds-bundle`
and `miopds-validate`.

## Repository layout

```text
miopds_common/
├── pyproject.toml
├── miopds_common/   # Python package (installed by pip)
└── examples/        # Sample shell scripts, Jinja2 templates and config files
    ├── scripts/
    ├── templates/
    └── config/
```

`examples/` is not installed by pip. Copy it into each instrument repository and
adapt it. See [examples/README.md](examples/README.md) for usage.
