"""Assemble the 1536x2288 atlas, recreating the two missing frames by
motion-compensated interpolation between adjacent frames of the same row."""

import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import gaussian_filter

CELLS = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells2"
OUTDIR = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
os.makedirs(OUTDIR, exist_ok=True)

meta = json.load(open(CELLS + "/meta.json"))
CW, CH, GW, GH = 192, 208, 1536, 2288
S, BASE = 0.96, 200

REQUIRED = {0: list(range(6)), 1: list(range(8)), 2: list(range(8)),
            3: list(range(4)), 4: list(range(5)), 5: list(range(8)),
            6: list(range(6)), 7: list(range(6)), 8: list(range(6)),
            9: list(range(8)), 10: list(range(8))}
# row -> {missing col: (frame A col, frame B col)}   (wrap-around of the loop)
SYNTH = {0: {5: (4, 0)}, 8: {5: (4, 0)}}

row_ground = {}
for r in range(11):
    bs = [i["bbox_cell"][1] + i["bbox_cell"][3] for i in meta[str(r)] if i]
    if bs:
        row_ground[r] = float(np.median(bs))


def place_cell(r, c):
    info = meta[str(r)][c]
    im = Image.open(f"{CELLS}/r{r}c{c}.png").convert("RGBA")
    bw, bh = info["bbox_cell"][2], info["bbox_cell"][3]
    sw, sh = max(1, int(round(bw * S))), max(1, int(round(bh * S)))
    small = np.array(im.resize((sw, sh), Image.LANCZOS))
    lx = (CW - sw) // 2
    ty = int(round(BASE + (info["bbox_cell"][1] - row_ground[r]) * S))
    cell = np.zeros((CH, CW, 4), np.uint8)
    sx0, sy0 = max(0, -lx), max(0, -ty)
    sx1, sy1 = min(sw, CW - lx), min(sh, CH - ty)
    if sy1 > sy0 and sx1 > sx0:
        cell[ty + sy0:ty + sy1, lx + sx0:lx + sx1] = small[sy0:sy1, sx0:sx1]
    return cell


def hs_flow(i1, i2, alpha=2.0, iters=400):
    u = np.zeros_like(i1)
    v = np.zeros_like(i1)
    def dx(a):
        return 0.5 * (np.roll(a, -1, axis=1) - np.roll(a, 1, axis=1))

    def dy(a):
        return 0.5 * (np.roll(a, -1, axis=0) - np.roll(a, 1, axis=0))
    ix = 0.5 * (dx(i1) + dx(i2))
    iy = 0.5 * (dy(i1) + dy(i2))
    it = i2 - i1
    k = np.array([[1 / 12, 1 / 6, 1 / 12], [1 / 6, 0, 1 / 6], [1 / 12, 1 / 6, 1 / 12]])
    for _ in range(iters):
        ub = ndimage.convolve(u, k, mode="nearest")
        vb = ndimage.convolve(v, k, mode="nearest")
        den = alpha ** 2 + ix ** 2 + iy ** 2
        u = ub - ix * (ix * ub + iy * vb + it) / den
        v = vb - iy * (ix * ub + iy * vb + it) / den
    return u, v


def warp(p, du, dv):
    h, w = p.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    out = np.empty_like(p)
    for ch in range(p.shape[2]):
        out[..., ch] = ndimage.map_coordinates(p[..., ch], [yy + dv, xx + du],
                                               order=1, mode="nearest")
    return out


def to_premul(a):
    al = a[..., 3:4] / 255.0
    return np.concatenate([a[..., :3] * al, a[..., 3:4]], axis=2)


def from_premul(p):
    al = p[..., 3:4] / 255.0
    rgb = np.where(al > 1e-6, p[..., :3] / np.maximum(al, 1e-6), 0.0)
    return np.concatenate([rgb, p[..., 3:4]], axis=2)


def synth(cell_a, cell_b, t=0.5):
    a = cell_a.astype(np.float64)
    b = cell_b.astype(np.float64)
    def lum(m):
        return gaussian_filter(
            0.299 * m[..., 0] + 0.587 * m[..., 1] + 0.114 * m[..., 2], 1.0)
    u, v = hs_flow(lum(a), lum(b))
    u = gaussian_filter(u, 1.5)
    v = gaussian_filter(v, 1.5)
    pa, pb = to_premul(a), to_premul(b)
    aw = warp(pa, -t * u, -t * v)
    bw = warp(pb, (1 - t) * u, (1 - t) * v)
    return np.clip(from_premul((1 - t) * aw + t * bw), 0, 255).astype(np.uint8)


# --- sanity: is the wrap-around pair as close as consecutive pairs? ---
for r in (0, 8):
    cells = [place_cell(r, c) for c in range(len([i for i in meta[str(r)] if i]))]
    n = len(cells)
    cons = [float(np.abs(cells[i].astype(float) - cells[(i + 1) % n].astype(float)).mean())
            for i in range(n - 1)]
    wrap = float(np.abs(cells[-1].astype(float) - cells[0].astype(float)).mean())
    print(f"row {r}: consecutive diffs={[round(x, 2) for x in cons]}  wrap(c_last,c0)={wrap:.2f}")

canvas = np.zeros((GH, GW, 4), np.uint8)
n_synth = 0
for r in range(11):
    for c in REQUIRED[r]:
        if r in SYNTH and c in SYNTH[r]:
            a_col, b_col = SYNTH[r][c]
            cell = synth(place_cell(r, a_col), place_cell(r, b_col))
            n_synth += 1
            print(f"  synthesised r{r}c{c} from r{r}c{a_col} + r{r}c{b_col}")
        else:
            cell = place_cell(r, c)
        canvas[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = cell
print("frames placed:", sum(len(v) for v in REQUIRED.values()), " synthesised:", n_synth)

# kill resampling specks and force transparent pixels to RGBA(0,0,0,0) so no
# codec can turn leftover colour data into visible blocks
al = canvas[..., 3]
canvas[..., 3] = np.where(al < 10, 0, al)
trans = canvas[..., 3] == 0
canvas[..., :3] = np.where(trans[..., None], 0, canvas[..., :3])

img = Image.fromarray(canvas, "RGBA")
img.save(OUTDIR + "/spritesheet.png")
img.save(OUTDIR + "/spritesheet.webp", lossless=True, method=0)
print("saved spritesheet.png / spritesheet.webp", img.size, img.mode)


def composite(bg):
    a = canvas[..., 3:4].astype(np.float64) / 255.0
    out = canvas[..., :3].astype(np.float64) * a + bg.astype(np.float64) * (1 - a)
    return np.clip(out, 0, 255).astype(np.uint8)


yy, xx = np.mgrid[0:GH, 0:GW]
sq = 16
check = np.zeros((GH, GW, 3), np.uint8)
m = ((xx // sq + yy // sq) % 2) == 0
check[m] = (70, 70, 74)
check[~m] = (46, 46, 50)
Image.fromarray(composite(check)).save(OUTDIR + "/contact-sheet.png")
Image.fromarray(composite(np.zeros((GH, GW, 3), np.uint8))).save(OUTDIR + "/preview-black.png")
print("saved contact-sheet.png (checkerboard) and preview-black.png")
