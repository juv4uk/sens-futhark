# Compiler-on-GPU slice evidence — 2026-10-06

Issue: #113
PR: #114
Research workflow: 37402218695 (#5)
Research artifact: 11385343994
Artifact SHA-256: d0a5ee0db688f3d851e9572403cf46c753f8a7c18ffe0c8fa1c3d0c7d3fb9efc
Measured code head: 801940b82ac6c48f777c2ad97a0639e4d6cd5f61

## Provenance

- SENS repository: juv4uk/sens
- SENS compiler-artifact producer commit: 1869fd5e51f38565ca968abceaa4bc933ae7a114
- artifact schema: compiler-compilation-artifact/1
- role-authority digest: 9768f683e90cfb56ca95675d1f6ac0e6ede91e21cebe97e20b455cf1b3094791
- Futhark: 0.27.1
- runner: wsm-gpu-sens-futhark
- CUDA capability probe: ready, WSL2, CUDA 12.6
- nvidia-smi: unavailable on runner; no fabricated GPU name/CC/driver fields
- source request bytes: 7404
- imported seed bytes: 72
- logical resident payload: 80 bytes (72-byte seed + 8-byte final scalar)

## CPU vs CUDA steady-state medians

| batch | C median us | CUDA median us | CUDA/C |
|---:|---:|---:|---:|
| 4096 | 38 | 388 | 0.0979x |
| 65536 | 578 | 1148 | 0.5035x |
| 1048576 | 12971 | 14963 | 0.8669x |
| 4194304 | 52417 | 57187 | 0.9166x |
| 8388608 | 158229 | 112578 | 1.4055x |
| 16777216 | 193229 | 228730 | 0.8448x |

## Phase medians

| batch | H2D us | kernel us | D2H us | phase sum us |
|---:|---:|---:|---:|---:|
| 4096 | 201.9 | 360.3 | 180.9 | 743.1 |
| 65536 | 136.0 | 1214.6 | 129.1 | 1479.7 |
| 1048576 | 186.4 | 16537.5 | 212.5 | 16936.4 |
| 4194304 | 231.6 | 60960.0 | 205.2 | 61396.8 |
| 8388608 | 209.7 | 133889.0 | 212.9 | 134311.6 |
| 16777216 | 151.2 | 245186.9 | 201.0 | 245539.1 |

## Verdict

The compiler legality/property scan executes correctly on CUDA and preserves exact
producer provenance, but this hardware does not show a stable end-to-end GPU
crossover. CUDA loses below 8M, wins at 8M (1.4055x), then loses again at 16M
(0.8448x). Therefore the result is **NO STABLE GPU ADVANTAGE** for this slice.

The 8M point is still useful: it shows a bounded region where GPU execution can
win after the seed is imported once. It does not justify automatic promotion or
a hard-coded threshold. Promotion should wait for a broader workload or a
repeatability study around the 8M region.

No SENS semantic authority moved into Futhark. No Sid8/Sens8 path was introduced.
GPU admission remains owned by CML #472.
