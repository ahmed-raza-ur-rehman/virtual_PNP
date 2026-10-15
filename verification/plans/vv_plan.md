# Verification & Validation Plan

## Levels
1. Unit (module-level) - directed + constrained-random, SVA, coverage.
2. Integration - subsystem (motion + encoder + SPI).
3. System - full trajectory execution, HIL.
4. Validation - end-to-end placement accuracy, throughput.

## Metrics
- Functional coverage > 95%
- Code coverage > 90%
- Timing closure at target clock
- Placement accuracy < 50 um (high-accuracy profile)
