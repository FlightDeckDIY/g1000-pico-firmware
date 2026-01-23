#!/usr/bin/env bash
set -euo pipefail

PORT="/dev/cu.usbmodem1101"

# Find all Python files (excluding .git) and copy them to the device root
files=$(find . -type f -name '*.py' -not -path '*/.git/*')

if [ -z "${files}" ]; then
  echo "No Python files found to sync."
  exit 1
fi

echo "Syncing the following files to ${PORT}:"
printf '%s
' ${files}

mpremote connect "${PORT}" cp ${files} :
