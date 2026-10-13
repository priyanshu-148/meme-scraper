"""
Turns finished memes into blank templates:
  1. EasyOCR finds all the text in the image
  2. A mask is drawn over that text
  3. Stable Diffusion inpainting repaints the masked area as background
  4. Only the masked area is replaced, the rest of the image stays untouched

Input:  meme_images/   (made by templates.py)
Output: blank_templates/   (plus blank_templates/masks/ so you can see what was erased)

First run downloads about 4 GB of models, so it takes a while. Click Run in VS Code.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import easyocr
import numpy as np
import torch
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image, ImageFilter

# ======== SETTINGS ========
IN_DIR = Path("meme_images")
OUT_DIR = Path("blank_templates")
MAX_IMAGES = 10          # start small to test, set to 0 to do all of them
STEPS = 25               # more = slightly better, slower
WORK_SIZE = 512          # the model repaints at this size, then it's scaled back up
MIN_CONF = 0.25          # OCR confidence needed to count something as text
MODEL = "stable-diffusion-v1-5/stable-diffusion-inpainting"
PROMPT = "plain clean background, seamless, natural continuation of the surrounding image"
NEGATIVE = "text, letters, words, caption, subtitles, watermark, logo, writing"
# ==========================


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def text_mask(reader, img: Image.Image) -> Image.Image | None:
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    found = 0
    for box, _text, conf in reader.readtext(arr):
        if conf < MIN_CONF:
            continue
        cv2.fillPoly(mask, [np.array(box, dtype=np.int32)], 255)
        found += 1
    if not found:
        return None
    k = max(7, int(min(h, w) * 0.02))        # grow the mask to cover outlines and shadows
    mask = cv2.dilate(mask, np.ones((k, k), np.uint8), iterations=2)
    return Image.fromarray(mask)


def inpaint(pipe, img: Image.Image, mask: Image.Image) -> Image.Image:
    w, h = img.size
    s = WORK_SIZE / max(w, h)
    nw, nh = max(64, int(w * s) // 8 * 8), max(64, int(h * s) // 8 * 8)
    out = pipe(
        prompt=PROMPT, negative_prompt=NEGATIVE,
        image=img.resize((nw, nh), Image.LANCZOS),
        mask_image=mask.resize((nw, nh), Image.NEAREST),
        height=nh, width=nw, num_inference_steps=STEPS, guidance_scale=7.5,
    ).images[0].resize((w, h), Image.LANCZOS)
    soft = mask.filter(ImageFilter.GaussianBlur(3))
    return Image.composite(out, img, soft)   # keep original pixels outside the text


def main():
    files = sorted(p for p in IN_DIR.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if not files:
        raise SystemExit(f"No images in {IN_DIR}/. Run templates.py first.")
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "masks").mkdir(exist_ok=True)

    device = pick_device()
    print(f"Using device: {device}")
    print("Loading text detector...")
    reader = easyocr.Reader(["en"], gpu=(device == "cuda"))
    print("Loading diffusion model (first run downloads ~4 GB)...")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        MODEL, torch_dtype=torch.float16 if device == "cuda" else torch.float32
    ).to(device)
    pipe.enable_attention_slicing()
    pipe.set_progress_bar_config(disable=True)

    done = 0
    for f in files:
        out_path = OUT_DIR / f"{f.stem}.png"
        if out_path.exists():
            continue
        if MAX_IMAGES and done >= MAX_IMAGES:
            break
        t0 = time.time()
        img = Image.open(f).convert("RGB")
        mask = text_mask(reader, img)
        if mask is None:
            img.save(out_path)
            print(f"{f.name}: no text found, copied as is")
        else:
            mask.save(OUT_DIR / "masks" / f"{f.stem}.png")
            inpaint(pipe, img, mask).save(out_path)
            print(f"{f.name}: text removed ({time.time() - t0:.0f}s)")
        done += 1

    print(f"\nDone. {done} templates saved in {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
