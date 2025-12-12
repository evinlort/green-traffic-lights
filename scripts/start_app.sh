#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$REPO_DIR/../.venv"

if [[ ! -d "$VENV_PATH" ]]; then
  echo "Virtual environment not found at $VENV_PATH"
  echo "Create it with: python3 -m venv .venv && source .venv/bin/activate"
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

REQUIREMENTS_FILE="$REPO_DIR/../requirements.txt"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  python -m pip install --requirement "$REQUIREMENTS_FILE"
else
  echo "requirements.txt not found at $REQUIREMENTS_FILE"
  exit 1
fi

CONFIG_FILE="$REPO_DIR/../.config"
if [[ -f "$CONFIG_FILE" ]]; then
  echo "Loading environment from $CONFIG_FILE"
  # Export all variables defined in the config file
  set -a
  source "$CONFIG_FILE"
  set +a
else
  echo "Config file not found at $CONFIG_FILE"
fi

export FLASK_APP=app
PORT=8000
echo "Starting Flask HTTPS (adhoc) on port ${PORT}"
exec flask run --host 0.0.0.0 --port "$PORT" --cert=adhoc
