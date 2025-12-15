#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

main() {
  echo "==> Checking Python version (need 3.9+)..."
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Please install Python 3.9+." >&2
    exit 1
  fi
  py_ver=$(python3 - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
)
  py_major=$(python3 - <<'PY'
import sys
print(sys.version_info.major)
PY
)
  py_minor=$(python3 - <<'PY'
import sys
print(sys.version_info.minor)
PY
)
  if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 9 ]; }; then
    echo "Python version $py_ver is too old. Please install Python 3.9+." >&2
    exit 1
  fi
  echo "Python OK: $py_ver"

  echo "==> Checking uv..."
  if ! command -v uv >/dev/null 2>&1; then
    if [ "${INSTALL_UV:-}" = "1" ]; then
      echo "uv not found. Installing via https://astral.sh/uv/install.sh ..."
      curl -LsSf https://astral.sh/uv/install.sh | sh
    else
      echo "uv not found. Install it first (see https://docs.astral.sh/uv/getting-started/installation/) or rerun with INSTALL_UV=1."
      exit 1
    fi
  fi
  echo "uv OK: $(uv --version)"

  echo "==> Checking ffmpeg..."
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg not found. Install it and re-run:"
    echo "  macOS: brew install ffmpeg"
    echo "  Debian/Ubuntu: sudo apt-get install ffmpeg"
    echo "  Windows: https://ffmpeg.org/download.html (add to PATH)"
    exit 1
  fi
  echo "ffmpeg OK: $(ffmpeg -version | head -n 1)"

  echo "==> Syncing environment with uv..."
  cd "$project_root"
  uv sync
  echo "Environment ready. Activate or use 'uv run' commands."
}

main "$@"
