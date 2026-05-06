# CLI Usage (Run Spec)

This repository supports running analyses headlessly (no GUI) using a **run spec JSON**.

A run spec can be:
- generated from the GUI via **Copy command line for this analysis**, or
- written/edited manually.

The run spec schema is defined in:
- `src/highway_segmentation_run_spec_schema.json`

## Install (developer-friendly)

Create and activate a venv (see README for OS-specific commands), then:

```bash
pip install -r requirements.txt
pip install -e .
```

The `pip install -e .` step installs this repository in editable mode and creates
the convenience commands:

- `highway-seg` (CLI)
- `highway-seg-gui` (GUI)

## Validate a run spec

```bash
highway-seg validate-spec --spec path/to/your.run_spec.json
```

Expected output:
- `OK`

## Run an analysis from a run spec

```bash
highway-seg run --spec path/to/your.run_spec.json
```

This writes the results JSON to the `output.output_json_path` location defined inside the run spec.

## Notes

- Paths are quoted in generated commands to support spaces (Windows and macOS/Linux).
- Relative paths in a run spec are resolved relative to the run spec file location.
- The CLI runner uses the same method registry as the GUI (`OPTIMIZATION_METHODS` in `src/config.py`).
- The runner writes results using `ExtensibleJsonResultsManager`, producing schema-compliant results JSON.
