"""
make_demo_assets.py
--------------------
Generates realistic-looking (but 100% synthetic / fictional) demo images
for the "How It Works" tab of the quantum-steganography Streamlit app:

    cover_demo.png        -> the decoy "ordinary photo"      (a real-ish landscape)
    secret_demo.png       -> the "classified" hidden payload (a mock intel report)
    stego_demo.png        -> visually identical to cover (imperceptible embedding)
    recovered_demo.png    -> visually identical to secret (pixel-exact recovery)
    encrypted_noise.png   -> AES ciphertext visualization
    diff_heatmap.png      -> amplified difference map (mostly black, a few flecks)

Nothing here depicts a real person, agency, document, or place. All text,
seals, and "coordinates" are invented for demonstration purposes only.

Run:  python make_demo_assets.py
Output: ./demo_assets/*.png  (drop this folder next to streamlit_app.py)
"""

import os
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

random.seed(7)
np.random.seed(7)

SIZE = 512
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_assets")
os.makedirs(OUT_DIR, exist_ok=True)

FONT_DIR = "/usr/share/fonts/truetype"
DEJAVU = os.path.join(FONT_DIR, "dejavu")
LIBERATION = os.path.join(FONT_DIR, "liberation")


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


F_SERIF_BOLD = os.path.join(DEJAVU, "DejaVuSerif-Bold.ttf")
F_SERIF = os.path.join(DEJAVU, "DejaVuSerif.ttf")
F_SANS_BOLD = os.path.join(LIBERATION, "LiberationSans-Bold.ttf")
F_SANS = os.path.join(LIBERATION, "LiberationSans-Regular.ttf")
F_MONO = os.path.join(LIBERATION, "LiberationMono-Regular.ttf")
F_MONO_BOLD = os.path.join(LIBERATION, "LiberationMono-Bold.ttf")


def add_grain(img, amount=8):
    arr = np.array(img).astype(np.int16)
    noise = np.random.normal(0, amount, arr.shape[:2])[:, :, None]
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def vignette(img, strength=0.35):
    w, h = img.size
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    dist = dist / dist.max()
    mask = 1 - strength * (dist ** 2)
    mask = np.clip(mask, 0, 1)
    arr = np.array(img).astype(np.float32)
    for c in range(arr.shape[2]):
        arr[:, :, c] *= mask
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# 1. COVER PHOTO — an ordinary-looking landscape (the decoy)

def make_cover():
    img = Image.new("RGB", (SIZE, SIZE), "white")
    px = img.load()

    top = np.array([255, 205, 140])
    mid = np.array([255, 165, 120])
    bot = np.array([120, 150, 190])
    horizon = int(SIZE * 0.55)
    for yv in range(horizon):
        t = yv / horizon
        if t < 0.6:
            c = top + (mid - top) * (t / 0.6)
        else:
            c = mid + (bot - mid) * ((t - 0.6) / 0.4)
        for xv in range(SIZE):
            px[xv, yv] = tuple(c.astype(int))
    for yv in range(horizon, SIZE):
        px_row = bot
        for xv in range(SIZE):
            px[xv, yv] = tuple(px_row.astype(int))

    img = img.filter(ImageFilter.GaussianBlur(1))
    draw = ImageDraw.Draw(img, "RGBA")

    # sun with soft glow
    sun_x, sun_y, sun_r = int(SIZE * 0.68), int(SIZE * 0.22), 34
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for r in range(140, sun_r, -4):
        alpha = int(35 * (1 - r / 140))
        gdraw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=(255, 250, 210, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(255, 244, 200))

    # soft clouds
    cloud_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(cloud_layer)
    for _ in range(10):
        cx = random.randint(0, SIZE)
        cy = random.randint(20, int(SIZE * 0.35))
        for _ in range(6):
            r = random.randint(18, 45)
            ox = cx + random.randint(-40, 40)
            oy = cy + random.randint(-8, 8)
            cdraw.ellipse([ox - r, oy - r * 0.5, ox + r, oy + r * 0.5], fill=(255, 255, 255, 60))
    cloud_layer = cloud_layer.filter(ImageFilter.GaussianBlur(8))
    img = Image.alpha_composite(img.convert("RGBA"), cloud_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # layered mountains, back to front with atmospheric perspective
    def jagged_ridge(base_y, amp, n, seed_offset):
        rnd = random.Random(seed_offset)
        pts = [(0, SIZE)]
        step = SIZE / n
        y = base_y
        for i in range(n + 1):
            xv = i * step
            y = base_y + rnd.randint(-amp, amp)
            pts.append((xv, y))
        pts.append((SIZE, SIZE))
        return pts

    layers = [
        (int(SIZE * 0.50), 26, (150, 165, 195), 1),
        (int(SIZE * 0.58), 34, (110, 135, 165), 2),
        (int(SIZE * 0.66), 46, (70, 105, 130), 3),
    ]
    for base_y, amp, color, seed in layers:
        pts = jagged_ridge(base_y, amp, 7, seed)
        draw.polygon(pts, fill=color)
        # snow caps on the nearest two ridgelines
        for i in range(1, len(pts) - 2):
            if pts[i][1] < base_y - amp * 0.4 and color[0] < 140:
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                draw.polygon([(x0 - 12, y0 + 10), (x0, y0), (x0 + 12, y0 + 10)],
                             fill=(250, 250, 255))

    # foreground tree line / hill
    hill_y = int(SIZE * 0.74)
    draw.polygon([(0, SIZE), (0, hill_y + 20), (SIZE * 0.3, hill_y - 10),
                  (SIZE * 0.55, hill_y + 15), (SIZE * 0.8, hill_y - 20),
                  (SIZE, hill_y + 10), (SIZE, SIZE)], fill=(35, 75, 45))
    for _ in range(14):
        tx = random.randint(0, SIZE)
        ty = hill_y + random.randint(-15, 30)
        th = random.randint(30, 55)
        draw.polygon([(tx, ty - th), (tx - 10, ty), (tx + 10, ty)], fill=(25, 60, 35))
        draw.rectangle([tx - 2, ty, tx + 2, ty + 10], fill=(60, 40, 25))

    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.12)
    img = add_grain(img, amount=4)
    img = vignette(img, 0.25)
    return img

# 2. "CLASSIFIED" DOCUMENT — a mock real-time intelligence report

def make_secret():
    W, H = SIZE, SIZE
    paper = np.array(Image.new("L", (W, H), 238))
    tex = (np.random.rand(H, W) * 14).astype(np.uint8)
    paper = np.clip(paper.astype(int) - tex, 0, 255).astype(np.uint8)
    img = Image.fromarray(paper).convert("RGB")
    img = ImageEnhance.Color(img).enhance(0.0)  # keep neutral paper tone
    img = Image.eval(img, lambda p: p)
    # warm the paper slightly
    arr = np.array(img).astype(np.float32)
    arr[:, :, 0] += 6
    arr[:, :, 1] += 2
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    draw = ImageDraw.Draw(img, "RGBA")
    margin = 26

    # classification banner (top + bottom)
    draw.rectangle([0, 0, W, 22], fill=(150, 20, 20))
    draw.text((W / 2, 11), "TOP SECRET // SIMULATED — FOR DEMONSTRATION ONLY",
              font=font(F_SANS_BOLD, 11), fill="white", anchor="mm")
    draw.rectangle([0, H - 22, W, H], fill=(150, 20, 20))
    draw.text((W / 2, H - 11), "NOT REAL — SYNTHETIC TEST DOCUMENT",
              font=font(F_SANS_BOLD, 11), fill="white", anchor="mm")

    y = 34
    draw.text((margin, y), "GLOBAL DEFENSE RESEARCH INITIATIVE", font=font(F_SERIF_BOLD, 17), fill=(25, 25, 25))
    y += 22
    draw.text((margin, y), "OFFICE OF ADVANCED SYSTEMS — FICTIONAL AGENCY, FOR DEMO USE",
              font=font(F_SANS, 10), fill=(70, 70, 70))
    y += 18
    draw.line([(margin, y), (W - margin, y)], fill=(60, 60, 60), width=1)
    y += 10

    draw.text((margin, y), "REF: QGS-2291-A", font=font(F_MONO, 11), fill=(30, 30, 30))
    draw.text((W - margin, y), "DATE-TIME: 09 SEP 2026  14:07Z", font=font(F_MONO, 11),
              fill=(30, 30, 30), anchor="ra")
    y += 20
    draw.text((margin, y), "SUBJECT: Real-time telemetry — prototype key-exchange field trial",
              font=font(F_SANS_BOLD, 12), fill=(20, 20, 20))
    y += 24

    # small "map/grid" thumbnail with a target marker
    map_x0, map_y0, map_w, map_h = margin, y, 150, 110
    draw.rectangle([map_x0, map_y0, map_x0 + map_w, map_y0 + map_h], fill=(210, 222, 205), outline=(90, 90, 90))
    gstep = 14
    for gx in range(map_x0, map_x0 + map_w, gstep):
        draw.line([(gx, map_y0), (gx, map_y0 + map_h)], fill=(180, 195, 175))
    for gy in range(map_y0, map_y0 + map_h, gstep):
        draw.line([(map_x0, gy), (map_x0 + map_w, gy)], fill=(180, 195, 175))
    rnd = random.Random(3)
    for _ in range(4):
        rx = rnd.randint(map_x0 + 10, map_x0 + map_w - 10)
        ry = rnd.randint(map_y0 + 10, map_y0 + map_h - 10)
        rw = rnd.randint(10, 22)
        draw.rectangle([rx, ry, rx + rw, ry + int(rw * 0.6)], outline=(70, 90, 70))
    tx_, ty_ = map_x0 + 96, map_y0 + 40
    draw.line([(tx_ - 8, ty_), (tx_ + 8, ty_)], fill=(180, 20, 20), width=2)
    draw.line([(tx_, ty_ - 8), (tx_, ty_ + 8)], fill=(180, 20, 20), width=2)
    draw.ellipse([tx_ - 12, ty_ - 12, tx_ + 12, ty_ + 12], outline=(180, 20, 20), width=2)
    draw.text((map_x0 + 4, map_y0 + map_h - 14), "GRID 14-A (SIMULATED)", font=font(F_MONO, 8), fill=(60, 60, 60))

    # telemetry table next to the map
    tbl_x = map_x0 + map_w + 16
    tbl_y = map_y0
    rows = [
        ("QUBIT STATE", "|+> superposition"),
        ("KEY LENGTH", "128-bit"),
        ("CIPHER", "AES-128-CTR"),
        ("CHANNEL", "open / public"),
        ("SIGNAL", "-71 dBm (sim)"),
    ]
    for i, (k, v) in enumerate(rows):
        ry = tbl_y + i * 20
        draw.text((tbl_x, ry), k, font=font(F_MONO_BOLD, 10), fill=(30, 30, 30))
        draw.text((tbl_x + 108, ry), v, font=font(F_MONO, 10), fill=(50, 50, 50))
    y = map_y0 + map_h + 14
    draw.line([(margin, y), (W - margin, y)], fill=(180, 180, 180), width=1)
    y += 10

    # a couple of "readable" narrative lines, then redacted bars
    draw.text((margin, y), "Field notes: synthetic payload generated for course demonstration",
              font=font(F_SERIF, 11), fill=(35, 35, 35))
    y += 16
    draw.text((margin, y), "of quantum-assisted key exchange and GAN-based image steganography.",
              font=font(F_SERIF, 11), fill=(35, 35, 35))
    y += 20

    for i in range(4):
        bar_w = random.randint(int(W * 0.35), int(W * 0.6))
        draw.rectangle([margin, y, margin + bar_w, y + 12], fill=(20, 20, 20))
        y += 18

    y += 6
    draw.text((margin, y), "DISTRIBUTION: cleared course personnel only (fictional restriction,",
              font=font(F_SANS, 9), fill=(90, 90, 90))
    y += 13
    draw.text((margin, y), "no real classification authority — created for a class project).",
              font=font(F_SANS, 9), fill=(90, 90, 90))

    # official-looking round seal
    seal_cx, seal_cy, seal_r = W - margin - 42, H - 70, 34
    draw.ellipse([seal_cx - seal_r, seal_cy - seal_r, seal_cx + seal_r, seal_cy + seal_r],
                 outline=(30, 60, 120), width=2)
    draw.ellipse([seal_cx - seal_r + 5, seal_cy - seal_r + 5, seal_cx + seal_r - 5, seal_cy + seal_r - 5],
                 outline=(30, 60, 120), width=1)
    draw.text((seal_cx, seal_cy - 6), "SIM", font=font(F_SERIF_BOLD, 14), fill=(30, 60, 120), anchor="mm")
    draw.text((seal_cx, seal_cy + 10), "DEMO SEAL", font=font(F_SANS, 7), fill=(30, 60, 120), anchor="mm")

    # diagonal TOP SECRET stamp
    stamp = Image.new("RGBA", (240, 90), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(stamp)
    sdraw.rectangle([4, 4, 236, 86], outline=(190, 20, 20, 230), width=4)
    sdraw.text((120, 45), "TOP SECRET", font=font(F_SANS_BOLD, 30), fill=(190, 20, 20, 220), anchor="mm")
    stamp = stamp.rotate(-14, expand=True, resample=Image.BICUBIC)
    img.paste(stamp, (W // 2 - stamp.width // 2 + 10, H // 2 - stamp.height // 2 - 6), stamp)

    img = img.rotate(0.3, resample=Image.BICUBIC, fillcolor=(238, 233, 222))
    img = add_grain(img, amount=3)
    img = vignette(img, 0.12)
    return img


# ----------------------------------------------------------------------
# 3. stego / recovered — visually the same as their originals
#    (the whole point of the demo is that they're indistinguishable /
#     pixel-exact); we add a whisper of noise to stego to make the
#     later "amplified difference" heatmap meaningful.
# ----------------------------------------------------------------------
def make_stego(cover_img):
    arr = np.array(cover_img).astype(np.int16)
    noise = np.random.randint(-2, 3, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def make_diff_heatmap(cover_img, stego_img, amplify=12):
    a = np.array(cover_img).astype(np.int16)
    b = np.array(stego_img).astype(np.int16)
    diff = np.abs(a - b).max(axis=2)  # per-pixel max channel delta, usually 0-2
    diff = np.clip(diff.astype(np.int32) * amplify, 0, 255).astype(np.uint8)
    heat = np.zeros((*diff.shape, 3), dtype=np.uint8)
    heat[:, :, 0] = diff  # red channel shows magnitude
    heat[:, :, 2] = (diff.astype(np.int32) * 2 // 3).clip(0, 255).astype(np.uint8)
    return Image.fromarray(heat)


def make_encrypted_noise():
    arr = np.random.randint(0, 256, (SIZE, SIZE, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img, "RGBA")
    band_h = 34
    band_y = SIZE // 2 - band_h // 2
    draw.rectangle([0, band_y, SIZE, band_y + band_h], fill=(0, 0, 0, 190))
    draw.text((SIZE / 2, band_y + band_h / 2), "AES-128-CTR CIPHERTEXT",
              font=font(F_MONO_BOLD, 15), fill=(80, 255, 140, 255), anchor="mm")
    return img


def make_qubit():
    img = Image.new("RGB", (SIZE, SIZE), (10, 14, 28))
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy, r = SIZE // 2, SIZE // 2 + 10, 150
    draw.ellipse([cx - r, cy - int(r * 0.35), cx + r, cy + int(r * 0.35)], outline=(70, 110, 200), width=2)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(70, 110, 200), width=2)
    draw.line([(cx, cy - r - 20), (cx, cy + r + 20)], fill=(70, 110, 200), width=1)
    draw.text((cx, cy - r - 34), "|0>", font=font(F_SANS_BOLD, 16), fill="white", anchor="mm")
    draw.text((cx, cy + r + 34), "|1>", font=font(F_SANS_BOLD, 16), fill="white", anchor="mm")
    ang = math.radians(55)
    ex, ey = cx - r * 0.85 * math.sin(ang), cy - r * 0.85 * math.cos(ang) * 0.9
    draw.line([(cx, cy), (ex, ey)], fill=(255, 190, 40), width=3)
    draw.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=(255, 190, 40))
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="white")
    draw.text((cx, 50), "Hadamard superposition", font=font(F_SANS_BOLD, 17), fill="white", anchor="mm")
    draw.text((cx, 74), "measured -> random bit", font=font(F_SANS, 12), fill=(160, 170, 200), anchor="mm")
    return img


def main():
    cover = make_cover()
    secret = make_secret()
    stego = make_stego(cover)
    diff = make_diff_heatmap(cover, stego)
    encrypted = make_encrypted_noise()
    qubit = make_qubit()

    cover.save(os.path.join(OUT_DIR, "cover_demo.png"))
    secret.save(os.path.join(OUT_DIR, "secret_demo.png"))
    stego.save(os.path.join(OUT_DIR, "stego_demo.png"))
    secret.save(os.path.join(OUT_DIR, "recovered_demo.png"))  # pixel-exact recovery
    diff.save(os.path.join(OUT_DIR, "diff_heatmap.png"))
    encrypted.save(os.path.join(OUT_DIR, "encrypted_noise.png"))
    qubit.save(os.path.join(OUT_DIR, "qubit_demo.png"))
    print("Saved 7 demo assets to:", OUT_DIR)


if __name__ == "__main__":
    main()