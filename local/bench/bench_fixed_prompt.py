#!/usr/bin/env python3
"""Fill-benchmark + scoring harness for the fixed agentic-coding prompt.

For each fill level (tokens of real text inserted before the task), sends the
SAME fixed prompt with a unique UUID sentinel line, temperature 0, thinking ON,
streams, and measures TTFT / decode t/s / prefill t/s. Writes full response to
disk for scoring. Run twice after server start: first run is JIT warmup (discard).

Usage:
  python bench_fixed_prompt.py <tag> <f1,f2,...> [--run 1|2] [--max-tokens N] \
      [--outdir bench/results/fixed] [--max-model-len 262144]
"""
import json, os, sys, time, uuid, urllib.request, urllib.error

FIXED_PROMPT = ("Now write a Python function merge_intervals(intervals) that merges "
    "overlapping ranges, handles edge cases (empty input, unsorted, touching intervals), "
    "includes type hints and a docstring, writes 5 unit tests, and explains its time and "
    "space complexity.")

API = os.environ.get("VLLM_API", "http://127.0.0.1:8000/v1")
KEY = os.environ.get("VLLM_API_KEY") or open(os.path.join(os.path.dirname(__file__), "..", "api_key.txt")).read().strip()
MODEL = "qwen3.8-27b"
MAX_MODEL_LEN = int(os.environ.get("MAX_MODEL_LEN", "262144"))
QUALITY_DATA = os.environ.get("QUALITY_DATA", os.path.join(os.path.dirname(__file__), "quality-data"))
DEFAULT_MAX_TOKENS = 32768

def load_corpus():
    import pyarrow.parquet as pq
    fb = pq.read_table(os.path.join(QUALITY_DATA, "fineweb2/data/dan_Latn/test/000_00000.parquet"),
                       columns=["text"]).column("text").to_pylist()
    # keep docs with reasonable length, cycle through them
    return [d for d in fb if 200 < len(d) < 4000]

def load_tokenizer():
    from transformers import AutoTokenizer
    model = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "models/Qwen3.8-27B-W4A16-AutoRound-fast"))
    return AutoTokenizer.from_pretrained(model)

def build_fill(corpus, tok, target_tokens):
    parts = []
    n = 0
    i = 0
    # first pass: estimate chars per token using a sample
    sample = " ".join(corpus[:40])
    cpt = len(sample) / max(1, len(tok.encode(sample)))
    needed_chars = int(target_tokens * cpt * 1.15)
    while n < target_tokens and len(parts) < 200000:
        d = corpus[i % len(corpus)]
        parts.append(d)
        n += len(tok.encode(d))
        i += 1
        if i > len(corpus) * 3:
            break
    text = "\n\n".join(parts)
    # trim to target (safety margin keeps it under)
    toks = tok.encode(text)
    if len(toks) > target_tokens:
        text = tok.decode(toks[:target_tokens], skip_special_tokens=True)
    return text

def stream_request(content, max_tokens):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(API + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t0 = time.time()
    ttft = None
    content_parts = []
    reason_parts = []
    finish = None
    usage = {}
    with urllib.request.urlopen(req, timeout=3600) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except Exception:
                continue
            choices = chunk.get("choices") or []
            if choices and ttft is None:
                ttft = time.time() - t0
            ch = choices[0] if choices else {}
            d = ch.get("delta", {})
            if d.get("content"):
                content_parts.append(d["content"])
            if d.get("reasoning"):
                reason_parts.append(d["reasoning"])
            if d.get("reasoning_content"):
                reason_parts.append(d["reasoning_content"])
            if ch.get("finish_reason"):
                finish = ch["finish_reason"]
            if chunk.get("usage"):
                usage = chunk["usage"]
    t1 = time.time()
    total = t1 - t0
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    decode_time = (t1 - t0) - (ttft or 0)
    return {
        "ttft_s": round(ttft, 3) if ttft is not None else None,
        "total_s": round(total, 3),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "gen_tps": round(ct / decode_time, 2) if decode_time > 0 else None,
        "pp_tps": round(pt / ttft, 1) if ttft else None,
        "finish_reason": finish,
        "content": "".join(content_parts),
        "reasoning": "".join(reason_parts),
    }

def main():
    tag = sys.argv[1]
    fills = [int(x) for x in sys.argv[2].split(",")]
    run = 1
    max_tokens = DEFAULT_MAX_TOKENS
    outdir = os.path.join(os.path.dirname(__file__), "results/fixed")
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--run": run = int(args[i+1]); i += 2
        elif args[i] == "--max-tokens": max_tokens = int(args[i+1]); i += 2
        elif args[i] == "--outdir": outdir = args[i+1]; i += 2
        else: i += 1
    os.makedirs(outdir, exist_ok=True)
    corpus = load_corpus()
    tok = load_tokenizer()
    print(f"# tag={tag} run={run} fills={fills} max_tokens={max_tokens}", flush=True)
    for F in fills:
        fill_text = build_fill(corpus, tok, F)
        uid = str(uuid.uuid4())
        content = f"UUID: {uid}\n\n{fill_text}\n\n{FIXED_PROMPT}"
        # ensure prompt+max_tokens fits in max model len
        pt_est = len(tok.encode(content))
        budget = min(max_tokens, MAX_MODEL_LEN - pt_est - 50)
        budget = max(budget, 256)
        r = stream_request(content, budget)
        fn = os.path.join(outdir, f"{tag}_fill{F}_run{run}.json")
        rec = {"tag": tag, "fill": F, "run": run, "uuid": uid,
               "max_tokens_requested": budget, **r}
        with open(fn, "w") as f:
            json.dump(rec, f)
        print(f"ROW fill={F} | TTFT={r['ttft_s']}s | pp={r['pp_tps']} t/s | "
              f"gen={r['gen_tps']} t/s | pt={r['prompt_tokens']} ct={r['completion_tokens']} | "
              f"finish={r['finish_reason']} | content_len={len(r['content'])} | reason_len={len(r['reasoning'])}",
              flush=True)

if __name__ == "__main__":
    main()
