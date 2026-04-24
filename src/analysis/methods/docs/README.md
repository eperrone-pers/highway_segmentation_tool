# Analysis Method Documentation

This folder contains method-specific documentation organized by `method_key`.

## Structure

- `src/analysis/methods/docs/<method_key>/README.md`

Where `<method_key>` matches the keys registered in `src/config.py` under `OPTIMIZATION_METHODS`.

## What to include per method

- Purpose / when to use
- Parameter definitions (what each UI field controls)
- How to interpret the results (plots + JSON fields)
- Known limitations / gotchas
- References (papers, standards, or source algorithm docs)
