import colorsys

import numpy as np
from PIL import Image

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"

png = Image.open(OUT + "/spritesheet.png").convert("RGBA")
webp = Image.open(OUT + "/spritesheet.webp").convert("RGBA")
a = np.array(png).astype(np.int16)
b = np.array(webp).astype(np.int16)
print("png vs webp max abs diff:", int(np.abs(a - b).max()))
print("png vs webp mean abs diff:", round(float(np.abs(a - b).mean()), 4))

alpha = a[..., 3]
print("opaque pixels:", int((alpha > 0).sum()))

rgb = a[..., :3]
mx = rgb.max(axis=2).astype(float)
mn = rgb.min(axis=2).astype(float)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)

op = alpha > 0
print("\nsaturation histogram of OPAQUE pixels:")
for lo, hi in [(0, .1), (.1, .2), (.2, .3), (.3, .5), (.5, .7), (.7, 1.01)]:
    n = int(((sat >= lo) & (sat < hi) & op).sum())
    print(f"  sat {lo:.1f}-{hi:.2f}: {n:,}")

# hue buckets of notably saturated opaque pixels
strong = op & (sat > 0.35)
print("\nhue buckets of saturated opaque pixels (sat>0.35):")
ys, xs = np.where(strong)
buckets = {}
for y, x in zip(ys[::7], xs[::7]):
    r, g, bl = rgb[y, x] / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, bl)
    deg = int(h * 360)
    key = deg // 30 * 30
    buckets[key] = buckets.get(key, 0) + 1
for k in sorted(buckets):
    print(f"  hue {k:3d}-{k + 29}: {buckets[k]}")

# check unused / transparent cells for stray non-zero RGB or alpha
USED = {0: range(5), 1: range(8), 2: range(8), 3: range(4), 4: range(5),
        5: range(8), 6: range(6), 7: range(6), 8: range(5), 9: range(8), 10: range(8)}
stray = []
for r in range(11):
    for c in range(8):
        if c in USED[r]:
            continue
        cell = a[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        if cell[..., 3].max() > 0:
            stray.append((r, c, int(cell[..., 3].max())))
print("\nunused cells with non-zero alpha:", stray)

# scanline check: alternating row means inside a cell
cell = a[0:208, 0:192, 3].astype(float)
rows_mean = cell.mean(axis=1)
d = np.abs(np.diff(rows_mean))
print("max row-to-row alpha mean delta in r0c0:", round(float(d.max()), 3))
