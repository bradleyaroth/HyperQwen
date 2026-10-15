#!/bin/bash
# Foreground (setsid) launcher for vision probes on :18021 — plan qwen-vision-uva §7.6.
# Usage: run_fg.sh <max_pixels> <image_limit> [logfile]
# Never tests through systemd (Restart=on-failure loop hazard, plan R3).
set -eu
MAXPX=${1:?max_pixels}
IMGLIM=${2:?image_limit}
LOG=${3:-/mnt/llm_storage/qwen-serving/qwen_vision_test.log}

cd /mnt/llm_storage/qwen-serving
CTX=huge PORT=18021 GPU_UTIL=0.90 MAX_LEN=220000 \
HF_HOME=/mnt/llm_storage/hf \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
QWEN3_5_VISION_UVA=1 \
EXTRA_ARGS="--enable-auto-tool-choice --tool-call-parser qwen3_coder --no-language-model-only --limit-mm-per-prompt.image $IMGLIM --limit-mm-per-prompt.video 0 --mm-processor-kwargs.min_pixels 65536 --mm-processor-kwargs.max_pixels $MAXPX --allowed-media-domains 192.168.13.240 192.168.13.246 dvbx1 dvbx1.reliantrack.local 192.168.13.242 llm.reliantrack.local localhost 127.0.0.1" \
setsid nohup single-user/start_qwen.sh > "$LOG" 2>&1 &
PGID=$(ps -o pgid= -p $! | tr -d ' ')
echo "started max_pixels=$MAXPX image_limit=$IMGLIM PGID=$PGID log=$LOG"
echo $PGID > /tmp/opencode/vis_pgid
