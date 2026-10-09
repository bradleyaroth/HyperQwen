#!/usr/bin/env python3
"""Functional checks for the qwen-vllm vision rollout (plan qwen-vision-uva §7.8).

Subcommands (API base from VLLM_API, default http://127.0.0.1:8000/v1):
  text      Danish smoke question, thinking off
  tool      tool-call smoke test (must return tool_calls)
  img       <file> [file2 ...] -- image readback; prints wall time, prompt_tokens,
            answer; polls nvidia-smi at ~100ms during the request and prints peak
  all       text + tool + the standard image battery (small, big, multi)
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

API = os.environ.get("VLLM_API", "http://127.0.0.1:8000/v1")
KEY = os.environ.get("VLLM_API_KEY") or open(
    os.path.join(os.path.dirname(__file__), "..", "api_key.txt")
).read().strip()
MODEL = "qwen3.8-27b"
IMGDIR = os.environ.get("IMGDIR", "/mnt/llm_storage/qwen-030-upgrade/assets/vistest")


def post(payload, timeout=600):
    req = urllib.request.Request(
        API + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY},
    )
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    return r, time.time() - t0


def data_uri(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


class VramPoller:
    def __enter__(self):
        self.fp = open("/tmp/opencode/vram_poll.csv", "w")
        self.p = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits",
             "-lms", "100"],
            stdout=self.fp)
        return self

    def __exit__(self, *a):
        self.p.terminate()
        self.p.wait()
        self.fp.close()
        vals = [int(x) for x in open("/tmp/opencode/vram_poll.csv").read().split()]
        self.peak = max(vals) if vals else -1
        self.base = vals[0] if vals else -1


def text_check():
    r, dt = post({"model": MODEL, "max_tokens": 8, "temperature": 0,
                  "messages": [{"role": "user",
                                "content": "Hvad er hovedstaden i Danmark? Svar med ét ord."}],
                  "chat_template_kwargs": {"enable_thinking": False}})
    ans = (r["choices"][0]["message"]["content"] or "").strip()
    ok = "københavn" in ans.lower() or "copenhagen" in ans.lower()
    print(f"TEXT {'PASS' if ok else 'FAIL'} answer={ans!r} ({dt:.2f}s)")
    return ok


def tool_check():
    payload = {
        "model": MODEL, "temperature": 0, "max_tokens": 200,
        "messages": [{"role": "user", "content":
                      "What is the weather in Aarhus right now? Use the tool."}],
        "tools": [{"type": "function", "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {"type": "object", "properties": {
                "city": {"type": "string"}}, "required": ["city"]}}}],
        "chat_template_kwargs": {"enable_thinking": False},
    }
    r, dt = post(payload)
    m = r["choices"][0]["message"]
    tc = m.get("tool_calls")
    if tc:
        print(f"TOOL PASS name={tc[0]['function']['name']} args={tc[0]['function']['arguments']} ({dt:.2f}s)")
        return True
    print(f"TOOL FAIL content={m.get('content')!r}")
    return False


def img_check(paths, expect=None, label=None):
    label = label or "+".join(os.path.basename(p) for p in paths)
    content = [{"type": "text", "text":
                "What text is in this image? Reply with the text only."}]
    for p in paths:
        content.append({"type": "image_url",
                        "image_url": {"url": data_uri(os.path.join(IMGDIR, p))}})
    with VramPoller() as vp:
        r, dt = post({"model": MODEL, "temperature": 0, "max_tokens": 400,
                      "messages": [{"role": "user", "content": content}],
                      "chat_template_kwargs": {"enable_thinking": False}})
    ans = (r["choices"][0]["message"]["content"] or "").strip()
    pt = r.get("usage", {}).get("prompt_tokens")
    ok = (expect.lower() in ans.lower()) if expect else None
    verdict = "PASS" if ok else ("INFO" if expect is None else "FAIL")
    print(f"IMG[{label}] {verdict} wall={dt:.2f}s prompt_tokens={pt} "
          f"vram_base={vp.base}MiB peak={vp.peak}MiB (+{vp.peak-vp.base})")
    print(f"  answer={ans!r}")
    return ok is not False, pt, dt, vp


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "text":
        sys.exit(0 if text_check() else 1)
    if cmd == "tool":
        sys.exit(0 if tool_check() else 1)
    if cmd == "img":
        sys.exit(0 if img_check(sys.argv[2:])[0] else 1)
    if cmd == "all":
        text_check()
        tool_check()
        img_check(["ocr_small.png"], expect="VISION OK 4721")
        img_check(["ocr_big.png"], expect="889021",
                  label="ocr_big(12MP)")
        img_check(["ocr_small.png", "ocr_a.png", "ocr_b.png", "ocr_c.png"],
                  expect="4721", label="4-images")
        print("done")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
