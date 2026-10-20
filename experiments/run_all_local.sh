#!/bin/bash
# Chạy toàn bộ thí nghiệm local (Ollama). Có resume: chạy lại sẽ bỏ qua câu đã xong.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
ALL=baseline,+linking,+fewshot,+semantic,+correction,+clarify,semantic_only,correction_only
$PY experiments/run_eventsql.py --llm ollama:qwen3:8b --configs $ALL --lang vi --seeds 0 --tag main
$PY experiments/run_eventsql.py --llm ollama:qwen3:8b --configs baseline,+fewshot,+semantic,+clarify --lang en --seeds 0 --tag main
$PY experiments/run_eventsql.py --llm ollama:qwen2.5:3b --configs baseline,+linking,+fewshot,+semantic,+correction,+clarify --lang vi --seeds 0 --tag main
$PY experiments/run_eventsql.py --llm ollama:qwen3:8b --configs baseline,+semantic,+clarify --lang vi --seeds 1,2 --tag main
