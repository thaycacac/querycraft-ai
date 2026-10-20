#!/bin/bash
# Phần còn lại của thí nghiệm local. Không dùng set -e: một bước lỗi không làm dừng cả chuỗi. Có resume.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY experiments/run_eventsql.py --llm ollama:qwen3:8b --configs baseline,+fewshot,+semantic,+clarify --lang en --seeds 0 --tag main
$PY experiments/run_eventsql.py --llm ollama:qwen2.5:3b --configs baseline,+linking,+fewshot,+semantic,+correction,+clarify --lang vi --seeds 0 --tag main
$PY experiments/run_public.py --dataset spider --n 200 --llm ollama:qwen3:8b --configs baseline,+linking --tag public
$PY experiments/run_public.py --dataset bird --n 200 --llm ollama:qwen3:8b --configs baseline,+linking,knowledge_only,+knowledge,+correction --tag public
$PY experiments/run_eventsql.py --llm ollama:qwen3:8b --configs baseline,+fewshot,+semantic --lang vi --seeds 1,2 --tag main
echo ALL_DONE
