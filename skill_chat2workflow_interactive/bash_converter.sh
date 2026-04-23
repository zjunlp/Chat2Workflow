#!/usr/bin/env bash
# Convert a <workflow> JSON (produced by the Chat2Workflow skill) to a
# platform-native configuration file.
#
# Usage:
#   bash bash_converter.sh <json_path> <workflow_name> <output_dir> <dify|coze>
#
# Example:
#   bash bash_converter.sh test.json test output/converter dify
#
# You can also replace --json_path with --json_str '{...}' to pass the JSON
# inline without creating a file.

set -euo pipefail

JSON_PATH="${1:-test.json}"
NAME="${2:-workflow}"
OUTPUT_PATH="${3:-output/converter}"
TYPE="${4:-dify}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python "${SCRIPT_DIR}/converter.py" \
    --json_path "${JSON_PATH}" \
    --name "${NAME}" \
    --output_path "${OUTPUT_PATH}" \
    --type "${TYPE}"
