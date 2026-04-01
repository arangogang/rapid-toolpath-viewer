"""
Generate ICO for ABB RAPID Toolpath Viewer.
Theme: 3D viewport feel — dark bg, robot arm path, coordinate axes, OpenGL grid.
"""
from PIL import Image, ImageDraw, ImageFont
import math, io, struct, os


def draw_icon(size):
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── Background: deep dark navy rounded square ─────────────────────────
    r = max(3, s // 7)
    d.rounded_rectangle([0, 0, s-1, s-1], radius=r, fill=(18, 24, 38, 255))

    # ── Perspective grid (floor plane) ────────────────────────────────────
    gc = (35, 55, 75, 160)
    lw = max(1, s // 64)
    # horizontal lines converging to vanishing point
    vx, vy = s * 0.5, s * 0.42   # vanishing point
    gy_bottom = s * 0.88
    gy_steps = [0.62, 0.72, 0.82, gy_bottom / s]
    gx_left, gx_right = s * 0.08, s * 0.92
    for gy_f in gy_steps:
        gy = s * gy_f
        # interpolate x spread based on depth
        t = (gy - vy) / (gy_bottom - vy)
        xl = vx + (gx_left - vx) * t
        xr = vx + (gx_right - vx) * t
        d.line([(xl, gy), (xr, gy)], fill=gc, width=lw)
    # vertical lines fanning from vanishing point
    for frac in [0.15, 0.30, 0.50, 0.70, 0.85]:
        gx = gx_left + (gx_right - gx_left) * frac
        d.line([(vx, vy), (gx, gy_bottom)], fill=gc, width=lw)

    # ── Coordinate axes (XYZ) ─────────────────────────────────────────────
    origin = (s * 0.28, s * 0.70)
    axis_len = s * 0.18
    alw = max(1, s // 28)
    # X axis → red
    d.line([origin, (origin[0] + axis_len, origin[1] - axis_len * 0.15)],
           fill=(220, 70, 70, 230), width=alw)
    # Y axis → green
    d.line([origin, (origin[0] - axis_len * 0.5, origin[1] - axis_len * 0.9)],
           fill=(70, 200, 100, 230), width=alw)
    # Z axis → blue (up)
    d.line([origin, (origin[0], origin[1] - axis_len)],
           fill=(80, 140, 240, 230), width=alw)

    # ── Toolpath curve: sweeping arc from lower-left to upper-right ───────
    accent = (0, 200, 220, 255)      # cyan
    accent2 = (0, 150, 180, 220)
    path_lw = max(2, s // 14)

    # Control points for a robot-arm-like path
    pts = [
        (s * 0.18, s * 0.75),
        (s * 0.30, s * 0.52),
        (s * 0.50, s * 0.38),
        (s * 0.68, s * 0.28),
        (s * 0.82, s * 0.20),
    ]

    # Draw smooth polyline with gradient feel
    for i in range(len(pts) - 1):
        alpha = int(180 + 75 * i / (len(pts) - 2))
        col = (0, 200 - i * 15, 220 - i * 10, min(255, alpha))
        d.line([pts[i], pts[i+1]], fill=col, width=path_lw)

    # ── Waypoint dots ─────────────────────────────────────────────────────
    dr = max(2, s // 18)
    for i, (px, py) in enumerate(pts):
        inner = max(1, dr - max(1, s // 40))
        d.ellipse([px-dr, py-dr, px+dr, py+dr], fill=(255, 255, 255, 200))
        d.ellipse([px-inner, py-inner, px+inner, py+inner], fill=accent)

    # ── End-effector target: crosshair circle at last point ───────────────
    ex, ey = pts[-1]
    er = max(3, s // 10)
    elw = max(1, s // 32)
    d.ellipse([ex-er, ey-er, ex+er, ey+er],
              outline=(255, 200, 0, 220), width=elw)
    d.line([(ex - er*1.4, ey), (ex + er*1.4, ey)],
           fill=(255, 200, 0, 160), width=elw)
    d.line([(ex, ey - er*1.4), (ex, ey + er*1.4)],
           fill=(255, 200, 0, 160), width=elw)

    return img


def build_ico(out_path):
    sizes = [16, 32, 48, 64, 128, 256]
    frames = [draw_icon(s) for s in sizes]

    png_blobs = []
    for img in frames:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_blobs.append(buf.getvalue())

    n = len(sizes)
    header_size = 6 + n * 16
    offsets, offset = [], header_size
    for blob in png_blobs:
        offsets.append(offset)
        offset += len(blob)

    with open(out_path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, n))
        for s, blob, off in zip(sizes, png_blobs, offsets):
            w = s if s < 256 else 0
            f.write(struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(blob), off))
        for blob in png_blobs:
            f.write(blob)

    print(f"ICO saved → {out_path}  |  frames: {sizes}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapid_viewer.ico")
    build_ico(out)
