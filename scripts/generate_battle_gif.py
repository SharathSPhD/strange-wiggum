"""
Generate agent-wars-battle.gif — standalone pixel-art battle animation.

Produces docs/agent-wars-battle.gif (600×280, ~30 frames, 12 fps).
Run from project root:
    python scripts/generate_battle_gif.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_PATH = Path("docs/agent-wars-battle.gif")

W, H = 600, 280
P = 4  # pixel scale (1 logical pixel = 4×4 screen pixels)
FPS = 12
DURATION = int(1000 / FPS)  # ms per frame

# Palette
BG       = (13, 13, 13)
GRID     = (25, 25, 25)
GREEN    = (57, 255, 20)
CYAN     = (0, 255, 255)
YELLOW   = (251, 216, 0)
RED      = (230, 57, 70)
BLUE     = (58, 134, 255)
BROWN    = (139, 90, 43)
WHITE    = (255, 255, 255)
BLACK    = (0, 0, 0)
ORANGE   = (255, 107, 53)
DARK_HEX = (20, 30, 40)
LIME     = (57, 255, 20)


def px(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple, w: int = 1, h: int = 1):
    """Draw a logical pixel block at (x, y) in pixel coordinates."""
    draw.rectangle([x * P, y * P, (x + w) * P - 1, (y + h) * P - 1], fill=color)


def draw_ralph(draw: ImageDraw.ImageDraw, cx: int, cy: int, bob: int = 0, flail: float = 0.0):
    """Ralph Wiggum pixel art.

    cx, cy: logical pixel centre-bottom of character
    bob: vertical offset for idle bob (0 or -1)
    flail: 0.0 = neutral, 1.0 = arms flailing
    """
    y0 = cy + bob

    # Hair (brown spikes)
    for hx, hy in [(-2, 0), (-1, -1), (0, -2), (1, -1), (2, 0)]:
        px(draw, cx + hx, y0 - 11 + hy, BROWN)

    # Head (yellow, 6×5)
    px(draw, cx - 3, y0 - 10, YELLOW, 6, 5)

    # Eyes (white + black pupil)
    px(draw, cx - 2, y0 - 9, WHITE, 2, 2)
    px(draw, cx + 1, y0 - 9, WHITE, 2, 2)
    px(draw, cx - 1, y0 - 8, BLACK)
    px(draw, cx + 2, y0 - 8, BLACK)

    # Mouth (grin)
    px(draw, cx - 2, y0 - 6, BLACK, 5, 1)
    px(draw, cx - 2, y0 - 5, WHITE, 5, 1)

    # Body / shirt (red, 5×4)
    px(draw, cx - 2, y0 - 4, RED, 5, 4)

    # Arms
    arm_dy = int(flail * 3)
    px(draw, cx - 4, y0 - 3 - arm_dy, RED, 2, 2)  # left arm
    px(draw, cx + 3, y0 - 3 + arm_dy, RED, 2, 2)  # right arm (mirror flail)

    # Shorts (blue, 5×2)
    px(draw, cx - 2, y0, BLUE, 5, 2)

    # Legs
    px(draw, cx - 2, y0 + 2, YELLOW, 2, 2)
    px(draw, cx + 1, y0 + 2, YELLOW, 2, 2)

    # Shoes
    px(draw, cx - 3, y0 + 4, BLACK, 3, 1)
    px(draw, cx + 1, y0 + 4, BLACK, 3, 1)


def draw_af(draw: ImageDraw.ImageDraw, cx: int, cy: int, t: float, win: bool = False):
    """AttractorFlow pixel art.

    cx, cy: logical pixel centre-bottom of character
    t: animation time (0..1, loops)
    win: if True, particles spiral outward
    """
    import math
    y0 = cy

    # Dark hexagonal body (7×8)
    for bx, by, bw, bh in [
        (-3, -12, 6, 1),
        (-4, -11, 8, 6),
        (-3, -5,  6, 1),
    ]:
        px(draw, cx + bx, y0 + by, DARK_HEX, bw, bh)

    # Circuit lines on body
    px(draw, cx - 2, y0 - 10, CYAN, 1, 1)
    px(draw, cx,     y0 - 10, CYAN, 1, 1)
    px(draw, cx + 2, y0 - 10, CYAN, 1, 1)
    px(draw, cx - 1, y0 - 8,  CYAN, 3, 1)

    # Spiral eye (radial rings in white/cyan)
    px(draw, cx - 1, y0 - 9, WHITE, 2, 2)
    px(draw, cx,     y0 - 9, CYAN,  1, 1)

    # Orbiting particles (3, at 120° intervals)
    angles = [t * 6.28 + i * 2.09 for i in range(3)]
    radii  = [5, 7, 6]
    colors = [CYAN, LIME, ORANGE]
    scales = [1.5, 1.0, 1.2] if win else [1.0, 1.0, 1.0]
    for angle, r, color, scale in zip(angles, radii, colors, scales):
        r2 = r * scale
        ox = int(math.cos(angle) * r2)
        oy = int(math.sin(angle) * r2 * 0.5)
        px(draw, cx + ox, y0 - 8 + oy, color)

    # Legs (dark thin)
    px(draw, cx - 1, y0 - 1, DARK_HEX, 1, 3)
    px(draw, cx + 1, y0 - 1, DARK_HEX, 1, 3)

    # Feet
    px(draw, cx - 2, y0 + 2, CYAN, 2, 1)
    px(draw, cx + 1, y0 + 2, CYAN, 2, 1)


def draw_bg(draw: ImageDraw.ImageDraw):
    """Background with pixel grid."""
    draw.rectangle([0, 0, W, H], fill=BG)
    for gx in range(0, W, P * 4):
        draw.line([gx, 0, gx, H], fill=GRID)
    for gy in range(0, H, P * 4):
        draw.line([0, gy, W, gy], fill=GRID)


def draw_text_px(draw: ImageDraw.ImageDraw, text: str, lx: int, ly: int, color: tuple, scale: int = 1):
    """Tiny 3×5 pixel font for labels."""
    GLYPHS = {
        'A': "0110011110001", 'B': "1110100111001110", 'C': "0111100001000110",
        'D': "1110100010011110", 'E': "1111100011001111", 'F': "1111100011001000",
        'G': "0111100001010110", 'H': "1001100111001001", 'I': "111010001111",
        'J': "001000100110010", 'K': "100110100101001", 'L': "100010001001111",
        'M': "10001110110101001", 'N': "1000110011010011001", 'O': "0110100010010110",
        'P': "1110100111001000", 'Q': "0110100010110101", 'R': "1110100111001001",
        'S': "0111100001100111", 'T': "11100100001000010",
        'U': "1001100110010110", 'V': "1001100110100100",
        'W': "1000110001101011010001", 'X': "1001010100010101001",
        'Y': "1001010100001000010", 'Z': "1110001001001111",
        '0': "0110101110010110", '1': "010110010010111",
        '2': "0110000100100111", '3': "1110000100011110",
        '4': "1001100111100001", '5': "1111100011000111",
        '6': "0110100011010110", '7': "1110000100010001",
        '8': "0110100101010110", '9': "0110100101100110",
        '.': "00001", ':': "10001", '-': "000111000", ' ': "00000",
        '!': "01001001000001", '%': "11000100010001011",
        'μ': "00010001100101111", 'σ': "011101011011",
    }
    x = lx
    for ch in text.upper():
        g = GLYPHS.get(ch, GLYPHS[' '])
        w = (len(g) + 4) // 5
        for i, bit in enumerate(g):
            if bit == '1':
                r = i // w
                c = i % w
                draw.rectangle(
                    [(x + c) * scale, (ly + r) * scale,
                     (x + c) * scale + scale - 1, (ly + r) * scale + scale - 1],
                    fill=color
                )
        x += w + 1


def draw_score_bar(draw: ImageDraw.ImageDraw, lx: int, ly: int, label: str,
                   score: float, max_score: float, color: tuple, progress: float = 1.0):
    """Draw a labelled score bar."""
    bar_w = 50
    filled = int(bar_w * (score / max_score) * min(progress, 1.0))
    draw.rectangle([lx * P, ly * P, (lx + bar_w) * P, (ly + 2) * P], fill=(40, 40, 40))
    if filled > 0:
        draw.rectangle([lx * P, ly * P, (lx + filled) * P, (ly + 2) * P], fill=color)
    draw_text_px(draw, label, lx, ly - 5, color, scale=2)


def make_frame(phase: str, t: float, ralph_x: int, af_x: int, bar_progress: float = 0.0) -> Image.Image:
    """Render one animation frame."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    draw_bg(draw)

    bob = int((t * 4 % 2 > 1))
    flail = max(0.0, (t - 0.5) * 2) if phase == "clash" else 0.0

    # Floor line
    draw.line([0, H - 20, W, H - 20], fill=(40, 40, 40), width=2)

    floor_y = (H - 20) // P  # logical pixel y for character feet

    if phase in ("idle", "clash", "results"):
        draw_ralph(draw, ralph_x, floor_y, bob=bob, flail=flail)
        draw_af(draw, af_x, floor_y, t * 6.28,
                win=(phase == "results"))

    # VS text in centre
    cx_lx = W // (2 * P) - 2
    vs_color = GREEN if phase == "idle" else RED
    draw_text_px(draw, "VS", cx_lx, floor_y - 14, vs_color, scale=3)

    # CLASH explosion
    if phase == "clash" and t > 0.5:
        import math
        for i in range(12):
            angle = i * (6.28 / 12) + t * 3
            r = int(20 * (t - 0.5) * 2)
            ex = W // 2 + int(math.cos(angle) * r * P)
            ey = H // 2 + int(math.sin(angle) * r * P)
            draw.ellipse([ex - 2, ey - 2, ex + 2, ey + 2],
                         fill=[GREEN, CYAN, ORANGE, RED][i % 4])

    # Score bars in results phase
    if phase == "results":
        draw_score_bar(draw, 2, 3,  "RALPH  9.42", 9.42, 10.0, RED,    bar_progress)
        draw_score_bar(draw, 2, 13, "AF     9.63", 9.63, 10.0, CYAN,   bar_progress)

        winner_alpha = min(1.0, bar_progress * 2 - 1)
        if winner_alpha > 0:
            draw_text_px(draw, "AF WINS!", W // (2 * P) - 8, 3, CYAN, scale=3)

    # Phase label (top right)
    labels = {"idle": "READY", "clash": "FIGHT!", "results": "RESULT"}
    draw_text_px(draw, labels.get(phase, ""), W // P - 15, 2, GREEN, scale=2)

    return img


def generate_gif():
    import math

    frames: list[Image.Image] = []
    total_frames = 48  # 4 s at 12 fps

    for i in range(total_frames):
        t = i / total_frames  # 0..1

        # Phase split: 0-0.3 idle, 0.3-0.6 clash, 0.6-1.0 results
        if t < 0.30:
            phase = "idle"
            local_t = t / 0.30
            ralph_x = 15
            af_x    = W // P - 20
        elif t < 0.60:
            phase = "clash"
            local_t = (t - 0.30) / 0.30
            # Characters converge toward centre
            ralph_x = int(15 + (W // (2 * P) - 25) * local_t)
            af_x    = int((W // P - 20) - (W // (2 * P) - 25) * local_t)
        else:
            phase = "results"
            local_t = (t - 0.60) / 0.40
            ralph_x = W // (2 * P) - 15
            af_x    = W // (2 * P) + 5

        frame = make_frame(phase, local_t, ralph_x, af_x, bar_progress=local_t if phase == "results" else 0.0)
        frames.append(frame)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT_PATH,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=DURATION,
        optimize=False,
    )
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"Saved {OUT_PATH} ({len(frames)} frames, {size_kb} KB)")


if __name__ == "__main__":
    generate_gif()
