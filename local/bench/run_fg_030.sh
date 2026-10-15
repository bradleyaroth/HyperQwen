#!/bin/bash
# Foreground (setsid) launcher for the vLLM 0.30.0 candidate on :18021 — plan
# hyperqwen-030-upgrade §6 Phase 4 (arm A parity / arm B fp16-dequant). Mirrors the
# unit env (local/systemd/qwen-vllm.service) + vision drop-in
# (local/systemd/qwen-vllm.service.d/vision.conf) exactly, except PORT (8000 ->
# 18021) and the MODEL pin. Never tests through systemd (Restart=on-failure loop
# hazard, plan R3). Runs start_qwen.sh from THIS worktree; PATH/venv resolve via
# the worktree `venv` symlink -> /mnt/llm_storage/qwen-serving/venv-030 (§2.2).
# MODEL is the absolute prod-tree fast dir so the Phase 4 argv is byte-identical
# to cutover (G3.2 / warm compile cache, Phase 5 step 7).
# Usage: run_fg_030.sh [logfile]      (default: <worktree>/fg030.log)
# Stop:  kill -TERM -$(cat /tmp/opencode/fg030_pgid)   (negative = whole PGID)
set -eu
LOG=${1:-/mnt/llm_storage/qwen-serving-030/fg030.log}

REPO=/mnt/llm_storage/qwen-serving-030
cd "$REPO"
export PATH="$REPO/venv/bin:$PATH"   # venv symlink; broken until Phase 2 builds venv-030

# Exact unit + drop-in env for 0.30: CTX/PORT/GPU_UTIL/MAX_LEN/HF_HOME/
# PYTORCH_CUDA_ALLOC_CONF from the unit; VISION=1 + EXTRA_ARGS from vision.conf;
# KVARN_POOL_MEM_FRAC is the launcher's CTX=huge default, pinned here to match the
# live process env (the old stack exported it too).
CTX=huge PORT=18021 GPU_UTIL=0.90 MAX_LEN=220000 \
VISION=1 \
KVARN_POOL_MEM_FRAC=0.15 \
MODEL=/mnt/llm_storage/qwen-serving/models/Qwen3.8-27B-W4A16-AutoRound-fast \
HF_HOME=/mnt/llm_storage/hf \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
EXTRA_ARGS="--limit-mm-per-prompt.image 4 --limit-mm-per-prompt.video 0 --mm-processor-kwargs.size.shortest_edge 1003520 --mm-processor-kwargs.size.longest_edge 4194304 --allowed-media-domains 192.168.13.240 192.168.13.246 dvbx1 dvbx1.reliantrack.local 192.168.13.242 llm.reliantrack.local localhost 127.0.0.1" \
setsid nohup bash single-user/start_qwen.sh > "$LOG" 2>&1 &
PGID=$(ps -o pgid= -p $! | tr -d ' ')
echo "started fg030 :18021 PGID=$PGID log=$LOG"
echo $PGID > /tmp/opencode/fg030_pgid
