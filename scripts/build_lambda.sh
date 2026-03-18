#!/usr/bin/env bash
set -euo pipefail

LAMBDA_NAME="${1:?Usage: build_lambda.sh <api|worker|ingestion>}"

ROOT_DIR="/app"
BUILD_DIR="${ROOT_DIR}/build/${LAMBDA_NAME}"

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# Copy application code
cp -r src/while_i_slept_api "${BUILD_DIR}/"

# Copy lambda handler
cp -r lambda/${LAMBDA_NAME}/* "${BUILD_DIR}/"

python3 - <<PY
import os
import zipfile

build_dir = "/app/build/${LAMBDA_NAME}"
output_zip = "/app/build/${LAMBDA_NAME}_lambda.zip"

with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
    for root, _, files in os.walk(build_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, build_dir)
            archive.write(full_path, relative_path)
PY

echo "Built Lambda: ${LAMBDA_NAME}"
