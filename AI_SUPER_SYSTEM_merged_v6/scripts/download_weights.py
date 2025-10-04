#!/usr/bin/env bash
# Быстрая загрузка весов в Hugging Face cache (опционально)
python - <<'PY'
from huggingface_hub import snapshot_download
models = [
  "Qwen/Qwen2-7B-Instruct",
  "mistralai/Mixtral-8x7B-Instruct-v0.1",
  "mistralai/Mistral-7B-Instruct-v0.3"
]
for m in models:
    print("Downloading", m)
    snapshot_download(repo_id=m, local_dir_use_symlinks=False)
PY
