#!/usr/bin/env bash
# vLLM으로 Qwen/Qwen3.6-27B-FP8 모델을 OpenAI 호환 엔드포인트로 서빙한다.
#
# 사전 준비: conda env "vllm"에 vllm 설치되어 있어야 함.
#
# 사용법:
#   bash docs/project_26-1_IRRS/serve_qwen.sh
#
# 서버가 뜨면 http://localhost:8000/v1/chat/completions 로 요청 가능
# (generate_search_text.py가 이 엔드포인트를 사용한다).

# gpu-memory-utilization을 낮추고 max-model-len을 줄이고 --enforce-eager로 cudagraph를 꺼서 OOM을 방지한다
PYTORCH_ALLOC_CONF=expandable_segments:True conda run -n vllm vllm serve Qwen/Qwen3.6-27B-FP8 \
  --tensor-parallel-size 2 \
  --port 8000 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 4096 \
  --enforce-eager
