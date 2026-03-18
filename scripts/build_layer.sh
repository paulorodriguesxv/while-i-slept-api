#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
LAYER_DIR="${ROOT_DIR}/layers/python-dependencies"
LAYER_PYTHON_DIR="${LAYER_DIR}/python"
REQUIREMENTS_FILE="${ROOT_DIR}/requirements.txt"
LAYER_ZIP="${BUILD_DIR}/python_dependencies_layer.zip"

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
  echo "requirements.txt not found at ${REQUIREMENTS_FILE}" >&2
  exit 1
fi

command -v zip >/dev/null 2>&1 || {
  echo "zip command is required to build Lambda artifacts." >&2
  exit 1
}

rm -rf "${LAYER_DIR}"
rm -f "${LAYER_ZIP}"
mkdir -p "${LAYER_PYTHON_DIR}" "${BUILD_DIR}"

python3 -m pip install -r "${REQUIREMENTS_FILE}" -t "${LAYER_PYTHON_DIR}"

(
  cd "${LAYER_DIR}"
  zip -qr "${LAYER_ZIP}" python
)

echo "Built Lambda layer: ${LAYER_ZIP}"
