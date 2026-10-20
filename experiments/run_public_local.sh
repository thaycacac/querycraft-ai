#!/bin/bash
# Chạy Spider/BIRD (mẫu 200 câu, cố định bằng seed) bằng model local, sau khi chuỗi EventSQL xong.
cd "$(dirname "$0")/.."
while pgrep -f run_all_local.sh > /dev/null; do sleep 60; done
PY=.venv/bin/python
$PY experiments/run_public.py --dataset spider --n 200 --llm ollama:qwen3:8b --configs baseline,+linking --tag public
$PY experiments/run_public.py --dataset bird --n 200 --llm ollama:qwen3:8b --configs baseline,+linking,knowledge_only,+knowledge,+correction --tag public
