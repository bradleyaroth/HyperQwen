# Phase 0 BASELINE — gate battery on live :8000 (vLLM 0.27.1 + 47-patch series + qwen3_5-vision-uva)

- **Battery start:** 2026-10-09 13:37:41 CDT · **end:** 14:29:53 CDT · **elapsed 52m12s**
- Service: `qwen-vllm` active the whole time (never restarted/touched). Model dir commit: 410a635.
- Client: `/mnt/llm_storage/qwen-bench-venv/bin/python` (openai 3.27.0, transformers 5.15.0, pyarrow 26.0.0; jinja2 3.1.6 installed mid-battery — client venv only, needed by upstream residue_sweep.py).
- All scripts persisted under `phase0/scripts/` — Phase 4 must re-run them VERBATIM (G-V2 is a byte-exact oracle).

## Verdict table

| Gate | Verdict | Key number |
|---|---|---|
| G-T1 decode @10k | **PASS (baseline recorded)** | median 112.15 t/s, min 108.43 (N=5) |
| G-T1 decode @100k | **PASS (baseline recorded)** | median 68.49 t/s, min 67.67 (N=5) |
| G-T2 prefill @10k | baseline | median 2684.8 t/s (TTFT median 3.775 s) |
| G-T2 prefill @100k | baseline | median 1991.5 t/s (TTFT median 50.283 s) |
| G-T3 needle @210k | **PASS** | exact `CRIMSON-FALCON-8841`, pt=210,050 |
| G-T4 tool call | **PASS** | `get_weather({"city":"Paris","unit":"celsius"})`, valid JSON args |
| G-T4 reasoning | **PASS** | reasoning_content 147 ch, content clean (no think-tags), 19*21=399 |
| G-T5 api_smoke | **9/12 PASS (pre-state)** | 3 pre-state FAILs, see list below |
| G-T6 auth | **PASS** | /v1/models 401 no-key / 200 key; /health 200 no-key; /metrics **200 no-key (pre-state; expected 401 post)**; /metrics 200 key |
| G-T7 models | **PASS** | exactly `["qwen3.8-27b"]` |
| G-T8 streaming ≥60k | **PASS** | official openai client, pt=60,029, TTFT 26.53 s, 26 chunks, finish=stop, 0 parse errors |
| G-T9 PPL | baseline | en 10.7610 / da 10.9125 / code 3.0542 / **all 8.0914** (hist. phase3-cutover: 8.092) |
| G-T9 GSM8K-200 | baseline | **acc 0.570**, mean 533 tok (ran; elapsed-at-decision ~11 min < 75 min) |
| G-T10 residue subset | **PASS** | 3 sweeps, 0 broken of 30 pads; residues 4 AND 120 both ok (cov 1.00) |
| G-V1 OCR | **PASS** | all exact: VERIFY 8264 · VISION OK 4721 · 889021+314159 · multi4 all four |
| G-V2 cap oracle | **recorded** | see table below |
| G-V3 timing | recorded | cold big 25.34 s (≤28.6 ✓) · warm big 1.65 s · small first-touch 8.98 s, warm 0.46 s · multi4 32.05 s (>28 s plan target — pre-state) · tower warm ≈ 0.04–0.06 s/4MP |
| G-V4 limits | **PASS** | 5-image → 400; video item → 400 |
| G-V5 URL fetch | **PASS** | localhost:81231→ 200 exact readback (pt=1067); example.com → 400 allowlist error |
| G-O2 VRAM | recorded | settle 22,941 MiB; absolute peak 23,961 MiB (see notes) |
| G-O3 stress pair | **PASS** | 100k-gen (2048 tok, length) + 4×4MP image (16,110 pt, exact "889021"), no OOM, peak 23,961 MiB |
| G-O4 whisper | **PASS** | PID 1392455 unchanged, active, 660 MiB GPU (RSS 872 MiB — plan's "660 MiB" is the GPU figure) |
| G-O5 journal | **PASS** | 0× (OutOfMemory\|Traceback\|CUDA error\|stall) in 1,106 lines; no 5xx; 7 4xx all deliberate probes |
| G-E1 decode @200k | baseline (N=2) | median 49.02 t/s, min 47.91; pp median 1538.2; TTFT ~130.1 s |
| G-O1 KV pool | **PASS** | 293,333 tokens (band 278,666–308,000 = ±5%) |
| G-E2 vision tower time | baseline | warm 0.037–0.061 s per 4MP image (TTFT image − TTFT text) |
| G-E3 boot timeline | baseline | Model loading 13.97 GiB · init 30.18 s (compile 23.77 s) · warm boot ~73 s |


## G-T1 per-run table (raw)

| fill | run | TTFT s | prefill t/s | decode t/s | pt | ct | finish |
|---|---|---|---|---|---|---|---|
| 10000 | 1 | 3.765 | 2693.2 | 109.93 | 10141 | 4504 | stop |
| 10000 | 2 | 3.783 | 2679.3 | 114.00 | 10137 | 2021 | stop |
| 10000 | 3 | 3.792 | 2673.6 | 108.43 | 10138 | 6628 | stop |
| 10000 | 4 | 3.775 | 2684.8 | 113.39 | 10136 | 4232 | stop |
| 10000 | 5 | 3.769 | 2689.5 | 112.15 | 10136 | 4087 | stop |
| **10000** | **median** | **3.775** | **2684.8** | **112.15** | | | |
| **10000** | **min** | 3.765 | **2673.6** | **108.43** | | | |
| 100000 | 1 | 50.245 | 1992.9 | 67.67 | 100135 | 5171 | stop |
| 100000 | 2 | 50.286 | 1991.4 | 68.82 | 100140 | 6975 | stop |
| 100000 | 3 | 50.283 | 1991.5 | 67.82 | 100140 | 4495 | stop |
| 100000 | 4 | 50.271 | 1992.0 | 70.41 | 100139 | 5645 | stop |
| 100000 | 5 | 50.286 | 1991.4 | 68.49 | 100141 | 7008 | stop |
| **100000** | **median** | **50.283** | **1991.5** | **68.49** | | | |
| **100000** | **min** | 50.245 | **1991.4** | **67.67** | | | |
| 200000 (E1) | 1 | 129.837 | 1541.5 | 50.14 | 200139 | 3112 | stop |
| 200000 (E1) | 2 | 130.401 | 1534.8 | 47.91 | 200137 | 3805 | stop |
| **200000** | **median** | **130.119** | **1538.2** | **49.02** | | | |
| **200000** | **min** | 129.837 | **1534.8** | **47.91** | | | |

## G-V2 prompt_tokens oracle (byte-exact for Phase 4)

| asset | dims px | prompt_tokens |
|---|---|---|
| verify_small.png | 800×300 | **1067** |
| ocr_small.png | 800×300 | **1067** |
| ocr_a.png | 800×300 | **1067** |
| ocr_b.png | 800×300 | **1067** |
| ocr_c.png | 800×300 | **1067** |
| ocr_big.png (12MP→4MP cap) | 4032×3024 | **4064** |
| multi4 (a+b+c+verify, one message) | 4× | **4207** |
| ocr_small via URL fetch (GV5) | 800×300 | **1067** |

Consistency: identical requests → identical prompt_tokens every time. Small images all hit the min_pixels=1003520 upscale grid identically.

## G-T5 feature list (pre-state)

PASS: greedy determinism · logprobs/top_logprobs · n=2 · stop strings · json_schema structured output · min_tokens+penalties · streaming · thinking mode · 20k-token prompt
FAIL (pre-state — allowed to remain failing post; must not REGRESS further): **seeded sampling determinism** (temp=1.0+seed twice → different text) · **completions echo+logprobs** (HTTP 400) · **thinking_token_budget → expected 400, was accepted** (V2-runner feature)

## G-O2 VRAM

- settle (idle median, first 30 s): **22,941 MiB**; whole-battery min 22,941 MiB
- absolute peak: **23,961 MiB** (+1,020 MiB over settle), first reached in the GT3-needle/GT9-PPL window (~13:48) and **retained** to battery end (caching-allocator retention; the G-O3 stress pair and G-E1 200k did NOT exceed it)
- whisper 660 MiB GPU throughout; vLLM engine 23,276 MiB at end
- Phase-4 gate note: plan's "≤ pre peak + 150 MiB" → pre peak = 23,961; "≤ 23,900 absolute" is already exceeded by the PRE stack's retained plateau — compare like-for-like (peak vs peak, settle vs settle).

## G-O3 stress pair

text: pt=100,034, ct=2,048 (finish=length), wall 112.8 s, sha256 45efb706… · image (4×ocr_big): pt=16,110, answer `889021` exact, wall 81.7 s · VRAM during pair: peak 23,961 MiB · no OOM/journal errors.

## Trims / deviations (MUST repeat identically in Phase 4)

1. **GSM8K-200: NOT trimmed** (elapsed at decision ~11 min < 75 min) — Phase 4 runs it too.
2. **G-E1: N=2, not 3** (time). Phase 4 arm A/B: N=2 @200k.
3. **G-T10: 3 sweeps** — pinned `0 8` + `116 12` PLUS supplemental `108 10` (our corpus base lands at residue 6, so pads map to residues 6–13 / 122–5 / 114–123; supplement needed to cover residue 120). Corpus: `phase0/tools/labd_corpus.txt` sha256 d4926392719fb397077eefc9cd301f7c58510028490ab5d26529aca45b460cd1 — reuse the SAME file, do not rebuild.
4. **G-E1/G-T1 @200k invocation: `MAX_MODEL_LEN=219000`** env (script's −50 slack underestimates chat-template overhead at exactly 220,000 → 400). 10k/100k runs used script defaults.
5. **G-T8 script v2** (question + assertion fixed after attempt 1 asserted answer length instead of clean-completion; attempt 1 preserved as `gt8_streaming.attempt1.json`).
6. jinja2 3.1.6 installed into qwen-bench-venv (client-only) for upstream residue_sweep.py / apply_chat_template.

## Anomalies / observations

- **Vision first-touch penalty:** first processing of each new (or LRU-evicted) image ≈ 9.0 s (small) / 25.3 s (12MP); warm repeats 0.46 s / 1.65 s; ocr_big re-incurred 25.2 s after intervening requests (cache eviction). Warm tower-time estimate (TTFT image − TTFT text at equal prompt_tokens, server-calibrated): small ≈ 0.00 s, 4MP ≈ 0.04–0.06 s. The cold/first-touch path dominates latency — key comparison point for 0.30's bulk-copy offload.
- multi4 wall 32.05 s > plan's 28 s G-V3 target (that target is a Phase-4 acceptance number; pre-state recorded).
- `prompt_logprobs` PPL works at GPU_UTIL=0.90 (api_smoke's echo+logprobs 400 is an `echo`-path issue, not PPL).
- code-PPL caveat: quality_battery's code corpus = `venv/.../vllm/v1/core/*.py` — file set changes with venv-030; en/da are corpus-stable, code/all may shift for corpus reasons. Compare en/da primarily.
- /metrics keyless = 200 pre-state (the .246 Kuma scraper keeps working until cutover adds the bearer requirement).

## Artifacts

`gt6_auth.json` · `gt4_tools_reasoning.json` · `gt5_api_smoke.txt` · `gt3_needle.txt` · `gt8_streaming.json` (+attempt1) · `gt9_quality_ppl.{txt,json}` · `gt9_gsm8k.{txt,json}` · `gt10_residue_*.txt` (3) · `gv1_gv2_gv3_gv4_vision.json` · `gv3_tower.json` · `gv5_urlfetch.json` · `gt1_decode.json` · `ge1_decode_200k.json` · `gt1_runs/*.json` (12) · `go2_vram.json` + `go2_markers.log` + `go2_vram_battery.csv` (11,531 samples) · `go3_stress.json` · `go4_whisper_end.txt` · `go5_journal_full.txt` · `logs/*.log` · `scripts/*.py` · `tools/` (upstream bench tools sha-pinned + corpus)

## G0 recalibrations (binding for Phase 4)

Applied 2026-10-09 from the reviewer's G0 sign-off conditions. Where these differ from
plan §5, THESE numbers bind Phase 4/5:

- **G-O2 (VRAM):** post peak ≤ **24,111 MiB**, compared peak-vs-peak (pre peak 23,961 +
  150). The plan's "≤ 23,900 MiB absolute" is **DROPPED** — the PRE stack's retained
  plateau (23,961) already exceeds it. Settle gate unchanged: post settle ≤ 23,200 MiB.
- **G-V3 multi4:** post ≤ 32.05 s → **PASS**; (32.05, 33.65] → **CONDITIONAL** (one
  re-run allowed, pass iff the re-run is ≤ 32.05 s); > 33.65 s → **FAIL**. (Pre measured
  32.05 s; the plan's 28 s target was a pre-state miss, not a post gate.)
- All other absolute gates in plan §5 are unchanged.
