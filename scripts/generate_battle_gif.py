"""
Generate docs/agent-wars-battle.gif — pixel-faithful Python replica of the
HTML5 canvas battle animation in docs/index.html.

Samples every 5th JS frame (300 total → 60 GIF frames) at 83 ms each ≈ 12 fps.
Canvas dimensions match the HTML: 800×280, scale (P) = 4.

Run from project root:
    python scripts/generate_battle_gif.py
"""

from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_PATH = Path("docs/agent-wars-battle.gif")
W, H = 800, 280
P = 4            # JS `scale` variable
TOTAL_JS = 300   # JS TOTAL_FRAMES
SAMPLE_STEP = 5  # capture every Nth JS frame
MS_PER_FRAME = 83  # ~12 fps


# ── colour helpers ────────────────────────────────────────────────────────────

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def blend(base: tuple, over: tuple, alpha: float) -> tuple[int, int, int]:
    """Alpha-blend `over` onto `base` (alpha 0..1)."""
    return tuple(int(b * (1 - alpha) + o * alpha) for b, o in zip(base, over))


BG_COL   = (13,  13,  13)
GREEN    = (57,  255, 20)
CYAN     = (0,   255, 255)
YELLOW   = (255, 255, 0)
RED      = (255, 65,  65)
LIME     = (57,  255, 20)
ORANGE   = (255, 107, 53)


# ── drawing primitives ────────────────────────────────────────────────────────

def fill_rect(draw: ImageDraw.ImageDraw,
              x: float, y: float, w: float, h: float,
              color: tuple) -> None:
    x1, y1 = int(round(x)), int(round(y))
    x2, y2 = int(round(x + w)) - 1, int(round(y + h)) - 1
    if x2 >= x1 and y2 >= y1:
        draw.rectangle([x1, y1, x2, y2], fill=color)


def draw_circle(img: Image.Image,
                cx: float, cy: float, r: float,
                color: tuple, alpha: float = 1.0) -> None:
    """Draw a filled circle with optional alpha blend onto img."""
    if r <= 0:
        return
    r = int(round(r))
    cx, cy = int(round(cx)), int(round(cy))
    overlay = Image.new("RGB", img.size, (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    img.paste(overlay, mask=Image.new("L", img.size,
              int(255 * alpha)).crop((cx - r, cy - r, cx + r, cy + r)).resize(img.size) if False
              else _make_circle_mask(img.size, cx, cy, r, alpha))


def _make_circle_mask(size, cx, cy, r, alpha):
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * alpha))
    return mask


def radial_glow(img: Image.Image,
                cx: float, cy: float,
                inner_col: tuple, outer_col: tuple,
                max_r: float, steps: int = 8) -> None:
    """Simulate a radial gradient by drawing concentric circles."""
    for i in range(steps, 0, -1):
        t = i / steps
        r = max_r * t
        col = blend(outer_col, inner_col, 1 - t)
        a = (1 - t) * 0.7 + 0.3  # fade towards edge
        draw_circle(img, cx, cy, r, col, a)


# ── character drawing ─────────────────────────────────────────────────────────

def draw_ralph(img: Image.Image, cx: float, cy: float, frame: int) -> None:
    """Replicate JS drawRalph() exactly."""
    draw = ImageDraw.Draw(img)
    p = P
    t = math.sin(frame * 0.05) * p  # bob offset (float → round in fill_rect)

    # HAIR
    for dx, dy in [(-2, 0), (0, -1), (2, 0)]:
        fill_rect(draw, cx + (dx - 1) * p, cy + dy * p + t, p, p * 2, hex_to_rgb('#4a2800'))

    # HEAD yellow oval
    fill_rect(draw, cx - 4*p, cy + 0*p + t, 8*p, p,   hex_to_rgb('#fbd800'))
    for r in range(1, 6):
        fill_rect(draw, cx - 5*p, cy + r*p + t, 10*p, p, hex_to_rgb('#fbd800'))
    for r in range(6, 8):
        fill_rect(draw, cx - 4*p, cy + r*p + t, 8*p,  p, hex_to_rgb('#fbd800'))

    # EYES
    fill_rect(draw, cx - 3*p, cy + 2*p + t, 2*p, 2*p, (255, 255, 255))
    fill_rect(draw, cx + 1*p, cy + 2*p + t, 2*p, 2*p, (255, 255, 255))
    fill_rect(draw, cx - 2*p, cy + 3*p + t, p,   p,   (0, 0, 0))
    fill_rect(draw, cx + 2*p, cy + 3*p + t, p,   p,   (0, 0, 0))

    # CONFUSED "?" expression (every 120 frames, first 40)
    if frame % 120 < 40:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", p * 3)
        except Exception:
            font = ImageFont.load_default()
        draw.text((cx + 4*p, cy - p + t - p*2), '?', fill=YELLOW, font=font)

    # MOUTH
    fill_rect(draw, cx - 2*p, cy + 6*p + t, 4*p, p,   (255, 255, 255))
    fill_rect(draw, cx - 3*p, cy + 6*p + t, p,   p,   (204, 0, 0))
    fill_rect(draw, cx + 2*p, cy + 6*p + t, p,   p,   (204, 0, 0))

    # BODY - SHIRT
    fill_rect(draw, cx - 4*p, cy + 8*p  + t, 8*p, 4*p, hex_to_rgb('#e63946'))
    fill_rect(draw, cx - 6*p, cy + 9*p  + t, 2*p, 3*p, hex_to_rgb('#e63946'))
    fill_rect(draw, cx + 4*p, cy + 9*p  + t, 2*p, 3*p, hex_to_rgb('#e63946'))

    # SHORTS
    fill_rect(draw, cx - 4*p, cy + 12*p + t, 8*p, 4*p, hex_to_rgb('#3a86ff'))

    # LEGS
    fill_rect(draw, cx - 3*p, cy + 16*p + t, 2*p, 4*p, hex_to_rgb('#fbd800'))
    fill_rect(draw, cx + 1*p, cy + 16*p + t, 2*p, 4*p, hex_to_rgb('#fbd800'))

    # SHOES
    fill_rect(draw, cx - 4*p, cy + 20*p + t, 3*p, p,   (0, 0, 0))
    fill_rect(draw, cx + 1*p, cy + 20*p + t, 3*p, p,   (0, 0, 0))


def draw_attractor_flow(img: Image.Image, cx: float, cy: float, frame: int) -> None:
    """Replicate JS drawAttractorFlow() exactly."""
    draw = ImageDraw.Draw(img)
    p = P
    t = frame * 0.03  # rotation angle

    # HEXAGONAL BODY
    pts = []
    for i in range(6):
        angle = (i * math.pi / 3) - math.pi / 2
        r = 8 * p
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle) + p * 2))
    draw.polygon(pts, fill=(0, 14, 20))

    # CIRCUIT LINES
    for lx, ly in [(cx - 4*p, cy), (cx + 4*p, cy), (cx, cy - 4*p), (cx, cy + 4*p)]:
        draw.line([(cx, cy + p*2), (lx, ly + p*2)],
                  fill=(0, 64, 64), width=1)

    # SPIRAL EYE radial gradient
    radial_glow(img, cx, cy + p*2, (255, 255, 255), (0, 255, 255), 5*p, steps=6)

    # SPIRAL LINES
    for i in range(3):
        start = t + (i * math.pi * 2 / 3)
        pts = []
        r_base = (3 + i) * p * 0.7
        for step in range(20):
            a = start + (step / 19) * math.pi * 1.2
            r = r_base
            pts.append((cx + r * math.cos(a), cy + p*2 + r * math.sin(a)))
        if len(pts) >= 2:
            draw.line(pts, fill=CYAN, width=1)

    # ORBITING PARTICLES
    particles = [
        (10*p, 1.2,  CYAN,   int(1.5*p)),
        (13*p, -0.8, LIME,   p),
        (8*p,  2.0,  ORANGE, p),
    ]
    for r, speed, color, size in particles:
        angle = t * speed
        px_pos = cx + r * math.cos(angle)
        py_pos = cy + p*2 + r * math.sin(angle) * 0.5
        # Outer glow
        radial_glow(img, px_pos, py_pos, color, BG_COL, size * 2, steps=4)
        # Solid centre
        draw_circle(img, px_pos, py_pos, max(1, size), color, 1.0)

    # λ READOUT (blink every 30 frames)
    if (frame // 30) % 2 == 0:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", p * 2)
        except Exception:
            font = ImageFont.load_default()
        draw.text((cx - 4*p, cy + 13*p), 'λ=-0.85', fill=LIME, font=font)


# ── HP bars ───────────────────────────────────────────────────────────────────

def draw_hp_bar(draw: ImageDraw.ImageDraw,
                x: float, y: float, w: float,
                label: str, score: float, max_score: float, color: tuple) -> None:
    """Replicate JS drawHPBar()."""
    pct = score / max_score
    # Track
    fill_rect(draw, x, y + 16, w, 10, (51, 51, 51))
    # Fill
    fill_rect(draw, x, y + 16, w * pct, 10, color)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 8)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x, y + 2), f"{label} {score:.2f}", fill=color, font=font)


# ── scanlines ─────────────────────────────────────────────────────────────────

def apply_scanlines(draw: ImageDraw.ImageDraw) -> None:
    for y in range(0, H, 2):
        draw.rectangle([0, y, W, y], fill=(0, 0, 0, 26))  # ~10% black


# ── text helper ───────────────────────────────────────────────────────────────

def draw_text_center(draw: ImageDraw.ImageDraw,
                     text: str, y: float, size: int, color: tuple) -> None:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, fill=color, font=font)


# ── frame renderer ────────────────────────────────────────────────────────────

def render_frame(js_frame: int) -> Image.Image:
    """Render one frame, replicating drawBattleFrame(frame) exactly."""
    img = Image.new("RGB", (W, H), BG_COL)
    draw = ImageDraw.Draw(img)

    # GRID (very faint green)
    grid_col = blend(BG_COL, GREEN, 0.05)
    for x in range(0, W, 8):
        draw.line([(x, 0), (x, H)], fill=grid_col)
    for y in range(0, H, 8):
        draw.line([(0, y), (W, y)], fill=grid_col)

    # GROUND LINE
    ground_col = blend(BG_COL, GREEN, 0.3)
    draw.rectangle([0, H - 20, W, H - 18], fill=ground_col)

    phase   = js_frame // 60
    phase_t = (js_frame % 60) / 60

    if phase == 0:
        # IDLE — characters at their lanes
        ralph_x = W * 0.2
        af_x    = W * 0.8
        draw_ralph(img, ralph_x, H * 0.55, js_frame)
        draw_attractor_flow(img, af_x, H * 0.5, js_frame)
        draw_hp_bar(draw, 30, 20, 160, 'RALPH', 9.42, 10, RED)
        draw_hp_bar(draw, W - 190, 20, 160, 'AF', 9.63, 10, LIME)
        draw_text_center(draw, 'VS', H // 2 + P * 2, P * 4, YELLOW)

    elif phase == 1:
        # CLASH — characters converge
        ralph_x = W * 0.2 + (W * 0.3) * phase_t
        af_x    = W * 0.8 - (W * 0.3) * phase_t
        # Ralph trips near the end
        draw_ralph(img, ralph_x, H * 0.55, js_frame)
        draw_attractor_flow(img, af_x, H * 0.5, js_frame)
        # CLASH! text + particle burst
        if phase_t > 0.8:
            clash_alpha = 1 - ((phase_t - 0.8) / 0.2)
            col = blend(BG_COL, YELLOW, clash_alpha)
            draw_text_center(draw, 'CLASH!', int(H * 0.4), P * 6, col)
            for i in range(8):
                angle = (i / 8) * math.pi * 2
                r = 30 * (phase_t - 0.8) / 0.2
                ex = int(W / 2 + r * math.cos(angle))
                ey = int(H * 0.5 + r * math.sin(angle))
                c = [RED, YELLOW, CYAN, ORANGE][i % 4]
                draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=c)

    else:
        # RESULTS
        ralph_x = W * 0.22
        af_x    = W * 0.78
        draw_ralph(img, ralph_x, H * 0.55, js_frame)
        draw_attractor_flow(img, af_x, H * 0.5, js_frame)
        score_progress = min(1.0, phase_t * 3)
        draw_hp_bar(draw, 30, 20, 160, 'RALPH', 9.42 * score_progress, 10, RED)
        draw_hp_bar(draw, W - 190, 20, 160, 'AF', 9.63 * score_progress, 10, LIME)
        draw_text_center(draw, 'ATTRACTOR EDGES IT!', int(H * 0.15), P * 3,
                         blend(BG_COL, LIME, 0.9))
        draw_text_center(draw, 'p=0.480 ns  d=0.17', int(H * 0.25), P * 2, YELLOW)

    # SCANLINES
    for y in range(0, H, 2):
        draw.rectangle([0, y, W, y], fill=(0, 0, 0))
        # blend 10% black onto every even row
        # (PIL RGBA compositing would be cleaner; approximate with dim line)
    # Re-draw a faint dark stripe — skip full re-render, just dim
    scanline_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    so_draw = ImageDraw.Draw(scanline_overlay)
    for y in range(0, H, 2):
        so_draw.rectangle([0, y, W - 1, y], fill=(0, 0, 0, 26))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, scanline_overlay)
    img = img_rgba.convert("RGB")

    return img


# ── main ──────────────────────────────────────────────────────────────────────

def generate_gif():
    frames: list[Image.Image] = []
    js_frames = range(0, TOTAL_JS, SAMPLE_STEP)
    total = len(list(js_frames))
    for i, jf in enumerate(range(0, TOTAL_JS, SAMPLE_STEP)):
        frames.append(render_frame(jf))
        print(f"\r  Rendering frame {i+1}/{total}...", end="", flush=True)
    print()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT_PATH,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=MS_PER_FRAME,
        optimize=False,
    )
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"Saved {OUT_PATH}  ({len(frames)} frames · {W}×{H} · {size_kb} KB)")


if __name__ == "__main__":
    generate_gif()
