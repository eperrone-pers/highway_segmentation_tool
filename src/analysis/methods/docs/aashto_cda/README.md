# AASHTO CDA Statistical Analysis (`method_key`: `aashto_cda`)

## Purpose

Deterministic statistical segmentation using the Enhanced AASHTO Cumulative Difference Approach (CDA).

## References

- Canonical citation text: `CITATIONS.md`
- MATLAB reference implementation: `src/analysis/methods/docs/aashto_cda/aashto_cda.m`

## Parameters (UI)

See `src/config.py` for the authoritative parameter list and defaults.

- `alpha`: significance level for change point detection
- `method`: error estimation method (1/2/3)
- `use_segment_length`: whether the test scales by each segment length vs total length
- `min_segment_datapoints`: minimum points per segment
- `max_segments`: optional cap on segments per section between mandatory breakpoints
- `min_section_difference`: merge adjacent segments whose means are too similar (0 disables)
- `enable_diagnostic_output`: verbose console diagnostics + extra diagnostic fields in results JSON

## Outputs

- Breakpoints (mandatory + detected internal breakpoints)
- Deterministic segmentation results
- Optional diagnostics in the results JSON when enabled
