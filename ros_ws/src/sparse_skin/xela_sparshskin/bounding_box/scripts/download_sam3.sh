#!/usr/bin/env bash
# Request Hugging Face access, log in, and download gated SAM 3 weights.
set -euo pipefail

ACCESS_URL="https://huggingface.co/facebook/sam3"
TOKEN_URL="https://huggingface.co/settings/tokens"
REPO="facebook/sam3"
FILE="sam3.pt"
DEST="${BOUNDING_BOX_SAM3:-${HOME}/.cache/bounding_box/sam3.pt}"

open_url() {
    local url="$1"
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 || true
    elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "$url" >/dev/null 2>&1 || true
    fi
    echo "  ${url}"
}

already_logged_in() {
    python3 - <<'PY' >/dev/null 2>&1
from huggingface_hub import HfApi
HfApi().whoami()
PY
}

has_repo_access() {
    python3 - <<'PY' >/dev/null 2>&1
from huggingface_hub import hf_hub_url, get_hf_file_metadata
get_hf_file_metadata(hf_hub_url("facebook/sam3", "sam3.pt"))
PY
}

echo "=== 1. Request access to ${REPO} ==="
echo "Open this page, agree to the license, and wait until access is granted:"
open_url "${ACCESS_URL}"
if ! has_repo_access; then
    read -r -p "Press Enter after Hugging Face has approved access ... "
fi
if ! has_repo_access; then
    if already_logged_in; then
        echo "Still no access to ${REPO}. Check that the request was approved, then rerun." >&2
        exit 1
    fi
    echo "No access yet (login is next; approval is checked again after that)."
fi

echo
echo "=== 2. Hugging Face login ==="
if already_logged_in; then
    echo "Already logged in."
elif [[ -n "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}" ]]; then
    TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN}}"
    if command -v hf >/dev/null 2>&1; then
        hf auth login --token "${TOKEN}" --add-to-git-credential
    else
        huggingface-cli login --token "${TOKEN}" --add-to-git-credential
    fi
else
    echo "Create a token with read access:"
    open_url "${TOKEN_URL}"
    if command -v hf >/dev/null 2>&1; then
        hf auth login
    else
        huggingface-cli login
    fi
fi
if ! already_logged_in; then
    echo "Hugging Face login failed." >&2
    exit 1
fi
if ! has_repo_access; then
    echo "Logged in, but ${REPO} is still gated. Request access at:" >&2
    echo "  ${ACCESS_URL}" >&2
    exit 1
fi

echo
echo "=== 3. Download ${FILE} ==="
mkdir -p "$(dirname "${DEST}")"
python3 - "${DEST}" <<'PY'
import os
import shutil
import sys

from huggingface_hub import hf_hub_download

dest = sys.argv[1]
src = hf_hub_download(repo_id="facebook/sam3", filename="sam3.pt")
os.makedirs(os.path.dirname(dest), exist_ok=True)
if os.path.abspath(src) != os.path.abspath(dest):
    if os.path.lexists(dest):
        os.remove(dest)
    try:
        os.symlink(src, dest)
    except OSError:
        shutil.copy2(src, dest)
print(dest)
PY

echo
echo "SAM 3 weights are at: ${DEST}"
echo "Launch with:"
echo "  ros2 launch bounding_box launch_bounding_box.py model:=${DEST}"
