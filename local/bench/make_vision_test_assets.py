#!/usr/bin/env python3
"""Make PIL test images for the qwen-vllm vision rollout (plan qwen-vision-uva §7.4).

Outputs into /tmp/opencode/vistest/:
  ocr_small.png  800x300   large text  VISION OK 4721   (exact readback gate)
  ocr_a/b/c.png  800x300   large text  IMAGE A 1135 / B 2246 / C 3379  (multi-image)
  ocr_big.png    4032x3024 (~12 MP) grid of short words + small text, for the
                 max_pixels cap + latency + legibility check
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = "/tmp/opencode/vistest"
os.makedirs(OUT, exist_ok=True)


def load_font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_small(name, text):
    img = Image.new("RGB", (800, 300), "white")
    d = ImageDraw.Draw(img)
    f = load_font(72)
    bbox = d.textbbox((0, 0), text, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((800 - w) / 2 - bbox[0], (300 - h) / 2 - bbox[1]), text, fill="black", font=f)
    img.save(f"{OUT}/{name}")
    print(name, img.size)


def make_big():
    # 4032x3024 = 12,192,768 px ~ 12 MP phone-photo size
    W, H = 4032, 3024
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_big = load_font(140)
    f_small = load_font(44)
    # headline the model must read for the legibility check
    d.text((120, 100), "BIGIMAGE TOP CODE 889021", fill="black", font=f_big)
    # grid of small words, 6 cols x 4 rows, modest sizes
    words = [
        "alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
        "golf", "hotel", "india", "juliet", "kilo", "lima",
        "mike", "november", "oscar", "papa", "quebec", "romeo",
        "sierra", "tango", "uniform", "victor", "whiskey", "xray",
    ]
    for i, wd in enumerate(words):
        col, row = i % 6, i // 6
        x, y = 160 + col * 640, 500 + row * 600
        d.text((x, y), wd, fill="black", font=f_big)
        d.text((x, y + 180), wd.upper() + "-0" + str(i + 1), fill="black", font=f_small)
    d.text((120, H - 220), "BIGIMAGE BOTTOM CODE 314159", fill="black", font=f_big)
    img.save(f"{OUT}/ocr_big.png")
    print("ocr_big.png", img.size, f"{W*H/1e6:.1f} MP")


make_small("ocr_small.png", "VISION OK 4721")
make_small("ocr_a.png", "IMAGE A 1135")
make_small("ocr_b.png", "IMAGE B 2246")
make_small("ocr_c.png", "IMAGE C 3379")
make_big()
print("done")
