#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/app"
BUILD_DIR="${ROOT_DIR}/build"
LAYER_DIR="${ROOT_DIR}/layers/python-dependencies"
LAYER_PYTHON_DIR="${LAYER_DIR}/python"
REQUIREMENTS_FILE="${ROOT_DIR}/requirements.txt"
LAYER_ZIP="${BUILD_DIR}/python_dependencies_layer.zip"

rm -rf "${LAYER_DIR}"
rm -f "${LAYER_ZIP}"
mkdir -p "${LAYER_PYTHON_DIR}" "${BUILD_DIR}"

pip install -r "${REQUIREMENTS_FILE}" -t "${LAYER_PYTHON_DIR}"

python3 - <<'PY'
import os
import zipfile

layer_dir = "/app/layers/python-dependencies"
layer_zip = "/app/build/python_dependencies_layer.zip"

with zipfile.ZipFile(layer_zip, "w", zipfile.ZIP_DEFLATED) as archive:
    for root, _, files in os.walk(layer_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, layer_dir)
            archive.write(full_path, relative_path)
PY

echo "Built Lambda layer: ${LAYER_ZIP}"
