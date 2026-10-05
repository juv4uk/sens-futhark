# SENS GPU worker (#77)

This component is a persistent local bridge to CUDA. It is deliberately **not**
described as a fully GPU-resident operating-system or GitHub Actions runner.

## Boundary

- the socket listener and OS integration run on the host CPU;
- admitted numerical jobs execute on CUDA;
- the worker keeps the CUDA context warm between jobs;
- IPC binds only to `127.0.0.1`;
- only allowlisted operations are accepted;
- no arbitrary shell or Python execution is exposed.

The initial Windows host witness used:

- NVIDIA GeForce GTX 1050 Ti;
- compute capability 6.1;
- PyTorch 2.13.0+cu126;
- CUDA 12.6 as seen by PyTorch;
- 4 GB VRAM.

## Install on Windows

From PowerShell in this directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1
```

The installer copies `worker.py` and `client.py` to
`%USERPROFILE%\sens-gpu-runner` and registers the per-user scheduled task
`SENS GPU Runner`.

## Health

```powershell
python client.py --ping
```

## Benchmark

```powershell
python client.py --bench --n 1000000 --iters 200
```

The live installation witness on 2026-10-05 completed 200 vector additions over
1,000,000 float32 elements in about 25.93 ms of measured GPU time
(~0.13 ms/iteration).

## API

One JSON object per TCP line on localhost port 8765.

Allowlisted operations:

- `ping`
- `add`
- `mul`
- `sum`
- `matmul`
- `benchmark`

The default limit is 1,000,000 elements per input tensor and 10,000 benchmark
iterations. These limits are intentional for a 4 GB device.

## Safety / scheduling

Do not replace this with an infinite spin kernel on the Windows display GPU.
Keep CUDA dispatch bounded and short. A later device-side scheduler can batch
SENS opcodes into finite launches, but must remain compatible with the host's
watchdog/TDR constraints.

Shared physical-GPU arbitration remains owned by `juv4uk/cml#472`.
Self-hosted Actions listener lifecycle remains `#69`.
