#!/usr/bin/env bash
# Clone Hunyuan3D-Part and download the P3-SAM checkpoint.
set -euo pipefail

ROOT="${P3_SAM_ROOT:-${HOME}/.cache/p3_sam/Hunyuan3D-Part}"
WEIGHTS="${P3_SAM_CKPT:-${HOME}/.cache/p3_sam/weights/p3sam.safetensors}"

if [[ ! -f "${ROOT}/P3-SAM/demo/auto_mask.py" ]]; then
  mkdir -p "$(dirname "${ROOT}")"
  git clone --depth 1 https://github.com/Tencent-Hunyuan/Hunyuan3D-Part.git "${ROOT}"
fi

python3 - <<PY
from huggingface_hub import hf_hub_download
from pathlib import Path
dest = Path("${WEIGHTS}")
dest.parent.mkdir(parents=True, exist_ok=True)
path = hf_hub_download(
    repo_id="tencent/Hunyuan3D-Part",
    filename="p3sam/p3sam.safetensors",
    local_dir=str(dest.parent),
)
print(path)
PY

echo "upstream: ${ROOT}"
echo "weights:  ${WEIGHTS}"
