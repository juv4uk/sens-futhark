#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=tools/cuda-env.sh
source "$ROOT/tools/cuda-env.sh"

echo "== kernel =="
uname -a

echo
echo "== normalized CUDA host environment =="
cuda_env_print

echo
echo "== NVIDIA visibility =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L || true
else
  echo "nvidia-smi: not found"
fi

echo
echo "== WSL/native GPU libraries/devices =="
ls -l /dev/dxg /dev/nvidia* 2>/dev/null || true
if [[ -n "$CUDA_DRIVER_LIB" ]]; then
  ls -l "$CUDA_DRIVER_LIB"/libcuda.so* 2>/dev/null || true
else
  echo "CUDA driver library directory: not found"
fi

echo
echo "== OpenCL loader =="
ldconfig -p 2>/dev/null | grep -F libOpenCL || echo "libOpenCL not found in ldconfig cache"

echo
echo "== OpenCL platforms =="
if command -v clinfo >/dev/null 2>&1; then
  clinfo -l || true
else
  echo "clinfo: not installed"
fi

echo
echo "== CUDA compiler =="
if command -v nvcc >/dev/null 2>&1; then
  nvcc --version | tail -n 5
else
  echo "nvcc: not found (not required for every CUDA client)"
fi

echo
echo "== CUDA capability record =="
cuda_env_json
