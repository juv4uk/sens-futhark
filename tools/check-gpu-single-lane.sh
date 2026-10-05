#!/usr/bin/env bash
# check-gpu-single-lane.sh — enforce the single-GPU-lane invariant (#82).
#
# One physical card => one scheduler (juv4uk/cml#472). Inside this repo that means:
#   * at most ONE workflow file may claim a GPU lane;
#   * that workflow must target the canonical self-hosted GPU runner,
#     never a hosted runner (no silent fallback).
#
# A workflow "claims a GPU lane" if it does CUDA work (cuda-env.sh, --backend=cuda,
# smoke-cuda, *-cuda targets, nvidia-smi) OR targets GPU runner labels. Detecting by
# work — not only by labels — is what catches a GPU workflow silently pointed at a
# hosted runner.
#
# Fail-closed: any violation exits non-zero. It never invents a pass.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WF_DIR="$ROOT/.github/workflows"

GPU_LABEL_RE='(gpu|cuda-[0-9]|gtx-|nvidia-)'
GPU_WORK_RE='(cuda-env\.sh|--backend=cuda|smoke-cuda|probe-cuda|nvidia-smi|test-[a-z0-9-]*-cuda|futhark[[:space:]]+cuda)'

if [[ ! -d "$WF_DIR" ]]; then
  echo "check-gpu-single-lane: no $WF_DIR; nothing to check"
  exit 0
fi

gpu_files=()
for f in "$WF_DIR"/*.yml "$WF_DIR"/*.yaml; do
  [[ -e "$f" ]] || continue
  label_hit=0
  grep -E '^[[:space:]]*runs-on:' "$f" | grep -Eq "$GPU_LABEL_RE" && label_hit=1
  work_hit=0
  grep -Eq "$GPU_WORK_RE" "$f" && work_hit=1
  if (( label_hit || work_hit )); then
    gpu_files+=("$(basename "$f")")
  fi
done

if (( ${#gpu_files[@]} == 0 )); then
  echo "check-gpu-single-lane: OK — no GPU lane claimed (0 workflows)"
  exit 0
fi

if (( ${#gpu_files[@]} > 1 )); then
  {
    echo "check-gpu-single-lane: FAIL-CLOSED — ${#gpu_files[@]} workflows claim a GPU lane:"
    printf '  - %s\n' "${gpu_files[@]}"
    echo "One physical card => one scheduler (cml#472). Collapse to a single GPU workflow."
  } >&2
  exit 2
fi

wf="$WF_DIR/${gpu_files[0]}"
runs_on="$(grep -E '^[[:space:]]*runs-on:' "$wf" || true)"

bad=0
if ! grep -q 'self-hosted' <<<"$runs_on"; then
  echo "check-gpu-single-lane: FAIL-CLOSED — ${gpu_files[0]} claims a GPU lane but is not self-hosted" >&2
  bad=1
fi
if ! grep -Eq "$GPU_LABEL_RE" <<<"$runs_on"; then
  echo "check-gpu-single-lane: FAIL-CLOSED — ${gpu_files[0]} claims a GPU lane but its runs-on has no GPU label" >&2
  bad=1
fi
if grep -Eq 'ubuntu-|windows-|macos-' <<<"$runs_on"; then
  echo "check-gpu-single-lane: FAIL-CLOSED — ${gpu_files[0]} GPU lane targets a hosted runner (silent-fallback risk)" >&2
  bad=1
fi

if (( bad )); then
  exit 2
fi

echo "check-gpu-single-lane: OK — single GPU lane in ${gpu_files[0]} (self-hosted, canonical)"
exit 0
