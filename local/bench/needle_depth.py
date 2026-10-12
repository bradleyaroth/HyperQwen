#!/usr/bin/env python3
"""Single-needle deep-context retrieval: bury a unique passphrase at ~depth tokens
of real text, then ask for it (thinking off). Verifies instruction/retrieval at depth."""
import json, os, sys, urllib.request
import pyarrow.parquet as pq

API = os.environ.get("VLLM_API", "http://127.0.0.1:8000/v1")
KEY = os.environ.get("VLLM_API_KEY") or open(os.path.join(os.path.dirname(__file__), "..", "..", "api_key.txt")).read().strip()
QUALITY_DATA = os.environ.get("QUALITY_DATA", os.path.join(os.path.dirname(__file__), "..", "..", "bench/quality-data"))
NEEDLE = "The secret passphrase is CRIMSON-FALCON-8841. Remember it exactly."
QUESTION = "What is the secret passphrase? Reply with only the passphrase and nothing else."

def build(depth):
    from transformers import AutoTokenizer
    t = AutoTokenizer.from_pretrained(os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "models/Qwen3.8-27B-W4A16-AutoRound-fast")))
    fb = pq.read_table(os.path.join(QUALITY_DATA, "fineweb2/data/dan_Latn/test/000_00000.parquet"), columns=["text"]).column("text").to_pylist()
    docs = [d for d in fb if 200 < len(d) < 4000]
    parts = []; n = 0; i = 0
    while n < depth:
        d = docs[i % len(docs)]; parts.append(d); n += len(t.encode(d)); i += 1
    fill = t.decode(t.encode("\n\n".join(parts))[:depth], skip_special_tokens=True)
    return fill, t

def ask(content, max_tokens=64):
    payload = {"model":"qwen3.8-27b","messages":[{"role":"user","content":content}],
        "temperature":0,"max_tokens":max_tokens,"chat_template_kwargs":{"enable_thinking":False}}
    req = urllib.request.Request(API+"/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+KEY})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    return r["choices"][0]["message"]["content"] or "", r["usage"]

def main():
    tag = sys.argv[1]; depth = int(sys.argv[2])
    fill, t = build(depth)
    # place needle at ~85% of the fill depth (deep, but before the end)
    cut = int(depth*0.85)
    content = fill[:cut] + "\n\n" + NEEDLE + "\n\n" + fill[cut:] + "\n\n" + QUESTION
    ans, usage = ask(content)
    ok = "CRIMSON-FALCON-8841" in ans
    pt = usage.get("prompt_tokens") if usage else None
    print("NEEDLE %s depth=%d | prompt_tokens=%s | found=%s | answer=%r" % (tag, depth, pt, ok, ans.strip()))
    print("RESULT:", "PASS" if ok else "FAIL")

if __name__ == "__main__":
    main()
