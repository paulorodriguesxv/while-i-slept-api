#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <lambda_name>" >&2
  echo "Example: $0 api" >&2
  exit 1
fi

LAMBDA_NAME="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
LAMBDA_DIR="${ROOT_DIR}/lambda/${LAMBDA_NAME}"
HANDLER_FILE="${LAMBDA_DIR}/handler.py"
SOURCE_DIR="${ROOT_DIR}/src/while_i_slept_api"
OUTPUT_ZIP="${BUILD_DIR}/${LAMBDA_NAME}_lambda.zip"

if [[ ! -d "${LAMBDA_DIR}" ]]; then
  echo "Lambda directory not found: ${LAMBDA_DIR}" >&2
  exit 1
fi

if [[ ! -f "${HANDLER_FILE}" ]]; then
  echo "Handler file not found: ${HANDLER_FILE}" >&2
  exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Source package not found: ${SOURCE_DIR}" >&2
  exit 1
fi

command -v zip >/dev/null 2>&1 || {
  echo "zip command is required to build Lambda artifacts." >&2
  exit 1
}

mkdir -p "${BUILD_DIR}"
TMP_DIR="$(mktemp -d "${BUILD_DIR}/${LAMBDA_NAME}.XXXXXX")"
trap 'rm -rf "${TMP_DIR}"' EXIT

cp "${HANDLER_FILE}" "${TMP_DIR}/handler.py"
cp -R "${SOURCE_DIR}" "${TMP_DIR}/while_i_slept_api"

rm -f "${OUTPUT_ZIP}"
(
  cd "${TMP_DIR}"
  zip -qr "${OUTPUT_ZIP}" .
)

echo "Built Lambda package: ${OUTPUT_ZIP}"
