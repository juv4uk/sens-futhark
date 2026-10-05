#!/usr/bin/env bash
# Shared CUDA host capability normalization for SENS execution substrates.
#
# Source this file to populate CUDA_* and loader/include paths, or execute it:
#   bash tools/cuda-env.sh env
#   bash tools/cuda-env.sh json
#   bash tools/cuda-env.sh run <command> [args...]

_cuda_prepend_path() {
  local name="$1"
  local value="$2"
  local current="${!name-}"

  [[ -n "$value" ]] || return 0
  case ":$current:" in
    *":$value:"*) ;;
    *)
      if [[ -n "$current" ]]; then
        printf -v "$name" '%s:%s' "$value" "$current"
      else
        printf -v "$name" '%s' "$value"
      fi
      export "$name"
      ;;
  esac
}

_cuda_find_driver_lib() {
  if [[ -n "${CUDA_DRIVER_LIB:-}" ]]; then
    printf '%s\n' "$CUDA_DRIVER_LIB"
    return 0
  fi

  if [[ -e /usr/lib/wsl/lib/libcuda.so.1 || -e /usr/lib/wsl/lib/libcuda.so ]]; then
    printf '%s\n' /usr/lib/wsl/lib
    return 0
  fi

  local candidate=""
  if command -v ldconfig >/dev/null 2>&1; then
    candidate="$(ldconfig -p 2>/dev/null | awk '/libcuda\.so(\.1)? / { print $NF; exit }')"
  fi
  if [[ -n "$candidate" ]]; then
    dirname "$candidate"
  fi
}

cuda_env_init() {
  CUDA_ROOT="${CUDA_HOME:-${CUDA_PATH:-/usr/local/cuda-12.6}}"

  if [[ -d "$CUDA_ROOT/targets/x86_64-linux" ]]; then
    CUDA_TARGET="$CUDA_ROOT/targets/x86_64-linux"
  else
    CUDA_TARGET="$CUDA_ROOT"
  fi

  CUDA_INCLUDE="${CUDA_INCLUDE:-$CUDA_TARGET/include}"

  if [[ -d "$CUDA_TARGET/lib" ]]; then
    CUDA_TOOLKIT_LIB="${CUDA_TOOLKIT_LIB:-$CUDA_TARGET/lib}"
  elif [[ -d "$CUDA_ROOT/lib64" ]]; then
    CUDA_TOOLKIT_LIB="${CUDA_TOOLKIT_LIB:-$CUDA_ROOT/lib64}"
  else
    CUDA_TOOLKIT_LIB="${CUDA_TOOLKIT_LIB:-$CUDA_TARGET/lib}"
  fi

  CUDA_DRIVER_LIB="$(_cuda_find_driver_lib)"

  export CUDA_ROOT CUDA_TARGET CUDA_INCLUDE CUDA_TOOLKIT_LIB CUDA_DRIVER_LIB
  export CUDA_HOME="$CUDA_ROOT"
  export CUDA_PATH="$CUDA_ROOT"

  _cuda_prepend_path CPATH "$CUDA_INCLUDE"
  _cuda_prepend_path LIBRARY_PATH "$CUDA_DRIVER_LIB"
  _cuda_prepend_path LIBRARY_PATH "$CUDA_TOOLKIT_LIB"
  _cuda_prepend_path LD_LIBRARY_PATH "$CUDA_DRIVER_LIB"
  _cuda_prepend_path LD_LIBRARY_PATH "$CUDA_TOOLKIT_LIB"
}

cuda_env_host_kind() {
  if [[ -e /dev/dxg ]]; then
    printf '%s\n' wsl2
  else
    printf '%s\n' native-linux
  fi
}

cuda_env_device_visible() {
  if [[ -e /dev/dxg ]]; then
    return 0
  fi

  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1
}

cuda_env_driver_present() {
  [[ -n "$CUDA_DRIVER_LIB" ]] &&
    { [[ -e "$CUDA_DRIVER_LIB/libcuda.so.1" ]] || [[ -e "$CUDA_DRIVER_LIB/libcuda.so" ]]; }
}

cuda_env_header_present() {
  [[ -f "$CUDA_INCLUDE/cuda.h" ]]
}

cuda_env_status() {
  local missing=()

  cuda_env_header_present || missing+=("cuda.h")
  cuda_env_driver_present || missing+=("libcuda")
  cuda_env_device_visible || missing+=("device")

  if ((${#missing[@]} == 0)); then
    printf '%s\n' ready
  else
    local IFS=,
    printf 'unavailable:%s\n' "${missing[*]}"
  fi
}

cuda_env_require() {
  local status
  status="$(cuda_env_status)"
  if [[ "$status" == ready ]]; then
    return 0
  fi

  printf 'CUDA host capability unavailable: %s\n' "${status#unavailable:}" >&2
  printf 'CUDA_ROOT=%s\n' "$CUDA_ROOT" >&2
  printf 'CUDA_INCLUDE=%s\n' "$CUDA_INCLUDE" >&2
  printf 'CUDA_TOOLKIT_LIB=%s\n' "$CUDA_TOOLKIT_LIB" >&2
  printf 'CUDA_DRIVER_LIB=%s\n' "$CUDA_DRIVER_LIB" >&2
  return 4
}

_cuda_json_escape() {
  local value="${1-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

_cuda_bool() {
  if "$@"; then
    printf '%s' true
  else
    printf '%s' false
  fi
}

cuda_env_json() {
  local status host_kind device_name="" driver_version="" compute_cap="" nvcc_version=""

  status="$(cuda_env_status)"
  host_kind="$(cuda_env_host_kind)"

  if command -v nvidia-smi >/dev/null 2>&1; then
    device_name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)"
    driver_version="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1 || true)"
    compute_cap="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 || true)"
  fi

  if command -v nvcc >/dev/null 2>&1; then
    nvcc_version="$(nvcc --version 2>/dev/null | awk '/release/ { print $0; exit }' || true)"
  fi

  printf '{'
  printf '"status":"%s",' "$(_cuda_json_escape "$status")"
  printf '"host_kind":"%s",' "$(_cuda_json_escape "$host_kind")"
  printf '"cuda_root":"%s",' "$(_cuda_json_escape "$CUDA_ROOT")"
  printf '"cuda_target":"%s",' "$(_cuda_json_escape "$CUDA_TARGET")"
  printf '"cuda_include":"%s",' "$(_cuda_json_escape "$CUDA_INCLUDE")"
  printf '"cuda_toolkit_lib":"%s",' "$(_cuda_json_escape "$CUDA_TOOLKIT_LIB")"
  printf '"cuda_driver_lib":"%s",' "$(_cuda_json_escape "$CUDA_DRIVER_LIB")"
  printf '"header_present":%s,' "$(_cuda_bool cuda_env_header_present)"
  printf '"driver_present":%s,' "$(_cuda_bool cuda_env_driver_present)"
  printf '"device_visible":%s,' "$(_cuda_bool cuda_env_device_visible)"
  printf '"device_name":"%s",' "$(_cuda_json_escape "$device_name")"
  printf '"compute_capability":"%s",' "$(_cuda_json_escape "$compute_cap")"
  printf '"driver_version":"%s",' "$(_cuda_json_escape "$driver_version")"
  printf '"nvcc_version":"%s"' "$(_cuda_json_escape "$nvcc_version")"
  printf '}\n'
}

cuda_env_print() {
  printf 'CUDA_ROOT=%s\n' "$CUDA_ROOT"
  printf 'CUDA_TARGET=%s\n' "$CUDA_TARGET"
  printf 'CUDA_INCLUDE=%s\n' "$CUDA_INCLUDE"
  printf 'CUDA_TOOLKIT_LIB=%s\n' "$CUDA_TOOLKIT_LIB"
  printf 'CUDA_DRIVER_LIB=%s\n' "$CUDA_DRIVER_LIB"
  printf 'CUDA_HOST_STATUS=%s\n' "$(cuda_env_status)"
}

cuda_env_main() {
  cuda_env_init

  case "${1:-}" in
    env)
      cuda_env_print
      ;;
    json)
      cuda_env_json
      ;;
    run)
      shift
      (($# > 0)) || {
        echo "usage: $0 run <command> [args...]" >&2
        return 2
      }
      cuda_env_require || return $?
      exec "$@"
      ;;
    *)
      echo "usage: $0 {env|json|run <command> [args...]}" >&2
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  cuda_env_main "$@"
else
  cuda_env_init
fi
