"""Strict re-extraction from the original Gemini JPG.

Per cell only the single largest connected component (the Samoyed) is kept;
every other pixel - labels, checkerboard, neighbouring remnants, specks - is dropped.
"""

import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"
OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells2"
os.makedirs(OUT, exist_ok=True)

arr = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = arr.shape
mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn
val = mx

# checkerboard = two measured neutral-grey levels (~100 and ~122)
gray = (sat < 16) & (val >= 70) & (val <= 150)
fg = ~gray


def runs(mask, minlen=1, maxlen=10**9):
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    return [(int(a), int(b)) for a, b in zip(st, en) if minlen <= b - a <= maxlen]


nw = (sat < 15) & (mx >= 240)
text = runs(nw.mean(axis=1) > 0.006, 8, 35)
assert len(text) == 11, f"expected 11 label strips, got {len(text)}"
rows_y = [(text[i][1] + 3, text[i + 1][0] - 3 if i < 10 else H) for i in range(11)]

dog_rows = np.zeros_like(fg)
for y0, y1 in rows_y:
    dog_rows[y0:y1] |= fg[y0:y1]
cols = runs(dog_rows.mean(axis=0) > 0.004, 30)
assert len(cols) == 8, f"expected 8 columns, got {len(cols)}"
bounds = [0] + [(cols[i][1] + cols[i + 1][0]) // 2 for i in range(7)] + [W]
cols_x = [(bounds[i], bounds[i + 1]) for i in range(8)]

MIN_SPRITE = 3000
all_rows = []
counts = []
for r in range(11):
    row = []
    y0, y1 = rows_y[r]
    for c in range(8):
        x0, x1 = cols_x[c]
        lab, n = ndimage.label(fg[y0:y1, x0:x1], np.ones((3, 3)))
        info = None
        if n:
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            best = int(np.argmax(sizes)) + 1
            if sizes[best - 1] >= MIN_SPRITE:
                mask = ndimage.binary_fill_holes(lab == best)
                ys, xs = np.where(mask)
                bx0, bx1 = int(xs.min()), int(xs.max()) + 1
                by0, by1 = int(ys.min()), int(ys.max()) + 1
                sub_mask = mask[by0:by1, bx0:bx1]
                crop = arr[y0 + by0:y0 + by1, x0 + bx0:x0 + bx1]
                rgba = np.dstack([crop.astype(np.uint8),
                                  (sub_mask * 255).astype(np.uint8)])
                # fill transparent RGB with nearest character colour so LANCZOS
                # resampling cannot drag grey background into the silhouette
                if sub_mask.any() and not sub_mask.all():
                    _, (ii, jj) = ndimage.distance_transform_edt(~sub_mask, return_indices=True)
                    near = rgba[..., :3][ii, jj]
                    rgba[..., :3] = np.where(sub_mask[..., None], rgba[..., :3], near)
                Image.fromarray(rgba, "RGBA").save(f"{OUT}/r{r}c{c}.png")
                info = {"col": c, "area": int(sub_mask.sum()),
                        "bbox_cell": [bx0, by0, bx1 - bx0, by1 - by0]}
        row.append(info)
    counts.append(sum(1 for v in row if v))
    all_rows.append(row)
    print(f"row {r}: {counts[-1]} frames  cols={[v['col'] for v in row if v]}")

meta = {"_rows_y": rows_y, "_cols_x": cols_x}
for r in range(11):
    meta[str(r)] = all_rows[r]
json.dump(meta, open(OUT + "/meta.json", "w"), indent=1)
print("counts:", counts)
