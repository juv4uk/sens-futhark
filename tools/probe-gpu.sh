#!/usr/bin/env bash
set -u

echo "== kernel =="
uname -a

echo
echo "== NVIDIA visibility =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L || true
else
  echo "nvidia-smi: not found"
fi

echo
echo "== WSL GPU libraries/devices =="
ls -l /dev/dxg /dev/nvidia* 2>/dev/null || true
ls -l /usr/lib/wsl/lib/libcuda.so* 2>/dev/null || true

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
  echo "nvcc: not found"
fi
