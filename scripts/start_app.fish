#!/usr/bin/env fish

set script_dir (dirname (status --current-filename))
set venv_path "$script_dir/../.venv"

if not test -d $venv_path
    echo "Virtual environment not found at $venv_path"
    echo "Create it with: python3 -m venv .venv; source .venv/bin/activate.fish"
    exit 1
end

if not test -f "$venv_path/bin/activate.fish"
    echo "activate.fish not found in $venv_path/bin"
    echo "Ensure the virtual environment was created with Fish available."
    exit 1
end

if not source "$venv_path/bin/activate.fish"
    echo "Failed to activate virtual environment from $venv_path"
    exit 1
end

set requirements_file "$script_dir/../requirements.txt"
if test -f $requirements_file
    python -m pip install --requirement $requirements_file; or exit 1
else
    echo "requirements.txt not found at $requirements_file"
    exit 1
end

set -x FLASK_APP app
set port 8000
echo "Starting Flask HTTPS (adhoc) on port $port"
exec flask run --host 0.0.0.0 --port $port --cert=adhoc
