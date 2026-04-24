# Constrained Single-Objective (`method_key`: `constrained`)

## Purpose

Find a segmentation that minimizes within-segment variation while targeting a specific average segment length.

## When to use

- You need a single recommended segmentation
- You also need the average segment length to land near a target value

## Parameters (UI)

See `src/config.py` for the authoritative parameter list and defaults.

- Target average length and tolerance
- Penalty weight (how strongly the target is enforced)
- Segment length constraints (min/max)
- GA settings (population, generations, mutation, crossover, etc.)

## Outputs

- One optimized solution
- Constraint satisfaction summary (target vs achieved)
