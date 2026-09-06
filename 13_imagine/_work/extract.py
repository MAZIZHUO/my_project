import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"
OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells"
os.makedirs(OUT, exist_ok=True)

arr = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = arr.shape
mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn
val = mx

# checkerboard = neutral grey in the two measured levels (~100 and ~122)
gray = (sat < 16) & (val >= 70) & (val <= 150)
fg = ~gray


def runs(mask, minlen=1, maxlen=10**9):
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    return [(int(a), int(b)) for a, b in zip(st, en) if minlen <= b - a <= maxlen]


# --- 1. locate the 11 text label strips (thin isolated near-white bands) ---
nw = (sat < 15) & (mx >= 240)
nwprof = nw.mean(axis=1)
text = runs(nwprof > 0.006, 8, 35)
print("text strips:", len(text))
assert len(text) == 11

rows_y = []
for i in range(11):
    y0 = text[i][1] + 3
    y1 = text[i + 1][0] - 3 if i < 10 else H
    rows_y.append((y0, y1))
print("row regions:", rows_y)

# --- 2. columns, measured only on dog rows (text excluded) ---
dogmask = np.zeros_like(fg)
for y0, y1 in rows_y:
    dogmask[y0:y1] |= fg[y0:y1]
colprof = dogmask.mean(axis=0)
cols = runs(colprof > 0.004, 30)
print("cols:", len(cols), cols)
assert len(cols) == 8

# expand each column to midpoints of the gaps so no content is clipped
bounds = [0]
for i in range(len(cols) - 1):
    bounds.append((cols[i][1] + cols[i + 1][0]) // 2)
bounds.append(W)
cols_x = [(bounds[i], bounds[i + 1]) for i in range(8)]
print("col regions:", cols_x)

# --- 3. per-cell segmentation ---
meta = {}
counts = []
for r, (y0, y1) in enumerate(rows_y):
    row_info = []
    for c, (x0, x1) in enumerate(cols_x):
        sub = fg[y0:y1, x0:x1]
        lab, n = ndimage.label(sub, np.ones((3, 3)))
        if n == 0:
            row_info.append(None)
            continue
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s >= 400]
        if not keep:
            row_info.append(None)
            continue
        mask = np.isin(lab, keep)
        mask = ndimage.binary_fill_holes(mask)
        area = int(mask.sum())
        if area < 1500:
            row_info.append(None)
            continue
        ys, xs = np.where(mask)
        bx0, bx1 = int(xs.min()), int(xs.max()) + 1
        by0, by1 = int(ys.min()), int(ys.max()) + 1
        row_info.append({
            "col": c, "area": area,
            "bbox_cell": [bx0, by0, bx1 - bx0, by1 - by0],
            "bbox_src": [x0 + bx0, y0 + by0, bx1 - bx0, by1 - by0],
        })
        # save tight RGBA crop with a hard alpha for now
        crop = arr[y0 + by0:y0 + by1, x0 + bx0:x0 + bx1]
        m = mask[by0:by1, bx0:bx1]
        rgba = np.dstack([crop.astype(np.uint8), (m * 255).astype(np.uint8)])
        Image.fromarray(rgba, "RGBA").save(f"{OUT}/r{r}c{c}.png")
    counts.append(sum(1 for v in row_info if v is not None))
    meta[str(r)] = row_info
    print(f"row {r}: {counts[-1]} frames -> " +
          str([(v['col'], v['bbox_src'][2], v['bbox_src'][3]) for v in row_info if v]))

meta["_rows_y"] = rows_y
meta["_cols_x"] = cols_x
with open(OUT + "/meta.json", "w") as f:
    json.dump(meta, f, indent=1)
print("frame counts per row:", counts)
