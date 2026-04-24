#!/usr/bin/env bash
# Convert a <workflow> JSON (produced by the Chat2Workflow skill) to a
# platform-native configuration file.
#
# Usage:
#   bash bash_converter.sh <json_path> <workflow_name> <output_dir> <dify|coze>
#
# Example:
#   bash bash_converter.sh ../workflow.json test ../chat2workflow_output dify
#
# You can also replace --json_path with --json_str '{...}' to pass the JSON
# inline without creating a file.
#
# Safety: the converter refuses to write files inside the skill directory.
# If <output_dir> is omitted it defaults to a sibling directory of the
# skill (../chat2workflow_output), and any output_path that resolves
# inside the skill folder is automatically redirected by converter.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_PARENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_OUTPUT_PATH="${SKILL_PARENT_DIR}/chat2workflow_output"

JSON_PATH="${1:-${SKILL_PARENT_DIR}/workflow.json}"
NAME="${2:-workflow}"
OUTPUT_PATH="${3:-${DEFAULT_OUTPUT_PATH}}"
TYPE="${4:-dify}"

python "${SCRIPT_DIR}/converter.py" \
    --json_path "${JSON_PATH}" \
    --name "${NAME}" \
    --output_path "${OUTPUT_PATH}" \
    --type "${TYPE}"
