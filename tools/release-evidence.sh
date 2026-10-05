#!/usr/bin/env bash
# release-evidence.sh — emit the release evidence manifest (#34 / #36 / #81).
#
# Repo-agnostic by design: the same script drops into any repository in the
# ecosystem. Only the *defaults* point at sens-futhark; every knob overrides:
#
#   RELEASE_REPO             default: juv4uk/sens-futhark
#   RELEASE_WORKFLOW_FILE    default: futhark.yml         (the GPU-only workflow)
#   RELEASE_ARTIFACT_PREFIX  default: futhark-cuda-evidence-
#   RELEASE_SHA              default: git rev-parse HEAD
#   RELEASE_RUN_URL          optional; live green run URL (else derived via gh)
#   RELEASE_ARTIFACT_DIR     optional; local artifact dir (offline / fixture mode)
#
# Fail-closed: a required field that cannot be sourced from a *live* green run
# is left empty and the script exits non-zero. Empty fields => do not cut the
# release tag (#34). This script never invents a green run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"

RELEASE_REPO="${RELEASE_REPO:-juv4uk/sens-futhark}"
RELEASE_WORKFLOW_FILE="${RELEASE_WORKFLOW_FILE:-futhark.yml}"
RELEASE_ARTIFACT_PREFIX="${RELEASE_ARTIFACT_PREFIX:-futhark-cuda-evidence-}"
RELEASE_RUN_URL="${RELEASE_RUN_URL:-}"
RELEASE_ARTIFACT_DIR="${RELEASE_ARTIFACT_DIR:-}"
RELEASE_SHA="${RELEASE_SHA:-$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "")}"

# --- pinned canonical language source ---------------------------------
SENS_COMMIT=""
if [[ -f "$PIN" ]]; then
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Z0-9_]+=' "$PIN")
  SENS_COMMIT="${SENS_COMMIT:-}"
fi

# --- compiler version (host-control; may be overridden by the artifact) --
futhark_ver="unknown"
if [[ -x "$ROOT/.tools/bin/futhark" ]]; then
  futhark_ver="$("$ROOT/.tools/bin/futhark" --version 2>/dev/null | head -n1 || true)"
elif command -v futhark >/dev/null 2>&1; then
  futhark_ver="$(futhark --version 2>/dev/null | head -n1 || true)"
fi

# --- locate the live green run and its artifact ------------------------
run_url="$RELEASE_RUN_URL"
artifact_dir="$RELEASE_ARTIFACT_DIR"

have_gh=0
command -v gh >/dev/null 2>&1 && have_gh=1

if [[ -z "$run_url" && "$have_gh" -eq 1 ]]; then
  run_url="$(gh run list \
      --repo "$RELEASE_REPO" \
      --workflow "$RELEASE_WORKFLOW_FILE" \
      --commit "$RELEASE_SHA" \
      --status success \
      --limit 1 \
      --json url --jq '.[0].url' 2>/dev/null || true)"
fi

if [[ -z "$artifact_dir" && "$have_gh" -eq 1 && -n "$run_url" ]]; then
  run_id="$(gh run list \
      --repo "$RELEASE_REPO" \
      --workflow "$RELEASE_WORKFLOW_FILE" \
      --commit "$RELEASE_SHA" \
      --status success \
      --limit 1 \
      --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)"
  if [[ -n "$run_id" ]]; then
    artifact_dir="$(mktemp -d)"
    gh run download "$run_id" \
        --repo "$RELEASE_REPO" \
        -n "${RELEASE_ARTIFACT_PREFIX}${RELEASE_SHA}" \
        -D "$artifact_dir" 2>/dev/null || true
  fi
fi

# --- read the CUDA evidence the workflow actually published ------------
cuda_env=""
if [[ -n "$artifact_dir" && -d "$artifact_dir" ]]; then
  cuda_env="$(find "$artifact_dir" -name 'cuda.env' -type f 2>/dev/null | head -n1 || true)"
fi

cuda_backend=""; cuda_runner=""; cuda_futhark=""
if [[ -n "$cuda_env" && -f "$cuda_env" ]]; then
  cuda_backend="$(sed -n 's/^backend=//p'         "$cuda_env" | head -n1)"
  cuda_runner="$(sed -n 's/^runner=//p'           "$cuda_env" | head -n1)"
  cuda_futhark="$(sed -n 's/^futhark_version=//p' "$cuda_env" | head -n1)"
fi

# --- derive the manifest ----------------------------------------------
# GPU-only policy (#79): the CUDA witness is the sole delivery evidence. The
# CPU witness is an internal semantic reference, never a delivery claim.
cpu_witness="N/A (GPU-only policy #79)"
cuda_witness=""
if [[ "$cuda_backend" == "cuda" && -n "$run_url" ]]; then
  cuda_witness="accept (backend=cuda, runner=${cuda_runner:-?})"
fi

date_utc="$(date -u +%Y-%m-%dT%H:%MZ)"

manifest="$(cat <<EOF
repo=$RELEASE_REPO
repo_sha=$RELEASE_SHA
sens_pin=${SENS_COMMIT}
futhark_version=${cuda_futhark:-$futhark_ver}
cuda_toolkit=12.6
device=GTX 1050 Ti
policy=gpu-only
cpu_witness=$cpu_witness
cuda_witness=$cuda_witness
run_url=$run_url
date=$date_utc
EOF
)"
printf '%s\n' "$manifest"

# --- fail-closed ------------------------------------------------------
required=(repo_sha sens_pin futhark_version cuda_witness run_url)
missing=()
for key in "${required[@]}"; do
  val="$(printf '%s\n' "$manifest" | sed -n "s/^${key}=//p" | head -n1)"
  if [[ -z "$val" || "$val" == "unknown" ]]; then
    missing+=("$key")
  fi
done

if (( ${#missing[@]} )); then
  {
    echo
    echo "release-evidence: FAIL-CLOSED — missing required field(s): ${missing[*]}" >&2
    echo "No live green run sourced these; do NOT cut the release tag (#34)." >&2
    echo "Provide RELEASE_RUN_URL / RELEASE_ARTIFACT_DIR, or run where gh is authenticated." >&2
  } >&2
  exit 2
fi
