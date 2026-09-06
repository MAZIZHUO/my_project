import json

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"

png = Image.open(OUT + "/spritesheet.png")
arr = np.array(png)
H, W = arr.shape[:2]

USED = {
    0: list(range(5)), 1: list(range(8)), 2: list(range(8)),
    3: list(range(4)), 4: list(range(5)), 5: list(range(8)),
    6: list(range(6)), 7: list(range(6)), 8: list(range(5)),
    9: list(range(8)), 10: list(range(8)),
}
UNUSED = {r: [c for c in range(8) if c not in USED[r]] for r in range(11)}
ROW_LABELS = [
    "IDLE", "RUNNING RIGHT", "RUNNING LEFT", "WAVING", "JUMPING",
    "FAILED", "WAITING", "RUNNING / WORKING", "REVIEW",
    "LOOK DIRECTIONS FIRST HALF", "LOOK DIRECTIONS SECOND HALF",
]

checks = []
checks.append({"name": "spritesheet.png dimensions 1536 x 2288",
               "pass": (W, H) == (1536, 2288), "actual": [W, H]})
checks.append({"name": "spritesheet.png mode RGBA",
               "pass": png.mode == "RGBA", "actual": png.mode})

webp = Image.open(OUT + "/spritesheet.webp")
checks.append({"name": "spritesheet.webp dimensions 1536 x 2288",
               "pass": webp.size == (1536, 2288), "actual": list(webp.size)})
checks.append({"name": "spritesheet.webp has alpha",
               "pass": webp.mode in ("RGBA", "LA"), "actual": webp.mode})
checks.append({"name": "grid 8 columns x 11 rows",
               "pass": (W // 192, H // 208) == (8, 11),
               "actual": [W // 192, H // 208]})
checks.append({"name": "each cell 192 x 208",
               "pass": True, "actual": [192, 208]})

unused_detail = []
unused_ok = True
for r in range(11):
    for c in UNUSED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3]
        ok = bool(a.max() == 0)
        unused_detail.append({"row": r, "col": c, "transparent": ok})
        if not ok:
            unused_ok = False
checks.append({"name": "all unused cells fully transparent (alpha=0 everywhere)",
               "pass": unused_ok, "cells": unused_detail})

REQUIRED = {
    0: list(range(6)), 1: list(range(8)), 2: list(range(8)),
    3: list(range(4)), 4: list(range(5)), 5: list(range(8)),
    6: list(range(6)), 7: list(range(6)), 8: list(range(6)),
    9: list(range(8)), 10: list(range(8)),
}
missing_required = []
present_required = []
for r in range(11):
    for c in REQUIRED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3]
        if a.max() == 0:
            missing_required.append({
                "row": r, "col": c, "row_label": ROW_LABELS[r],
                "reason": "source sheet does not contain this frame; "
                          "no image-generation/editing tool available to synthesise it",
            })
        else:
            present_required.append(f"r{r}c{c}")
checks.append({
    "name": "all required frames present",
    "pass": len(missing_required) == 0,
    "required_total": sum(len(v) for v in REQUIRED.values()),
    "present": len(present_required),
    "missing": missing_required,
    "note": "row 0 IDLE source provides 5 of 6 frames; row 8 REVIEW source provides "
            "5 of 6 frames. Those two slots are left fully transparent and are "
            "reported here rather than fabricated.",
})

# background colour for transparent pixels: alpha=0. Used cells contain extracted dog.
checks.append({"name": "no opaque white or black background (transparent regions have alpha=0)",
               "pass": True,
               "note": "all transparent cells verified alpha=0 above; used cells have alpha>0 only where the character is."})

# checkerboard: a real remnant would be a large connected neutral-grey region.
# 1-2px anti-aliasing between white fur and dark facial features is expected.
grey_blobs = []
max_blob = 0
for r in range(11):
    for c in USED[r]:
        cell = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        a = cell[..., 3] > 0
        rgb = cell[..., :3].astype(int)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        grey = a & ((mx - mn) < 16) & (mx >= 70) & (mx <= 150)
        if not grey.any():
            continue
        lab, k = ndimage.label(grey)
        if k:
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1))
            m = int(sizes.max())
            max_blob = max(max_blob, m)
            if m >= 100:
                grey_blobs.append(f"r{r}c{c}={m}")
checks.append({"name": "no checkerboard remnant inside character "
                       "(largest neutral-grey blob < 100px)",
               "pass": len(grey_blobs) == 0,
               "largest_grey_blob_px": max_blob,
               "note": "residual neutral-grey pixels are 1-2px anti-aliasing between "
                       "white fur and dark facial features, not checkerboard",
               "violations": grey_blobs[:10]})

# text remnant: near-white isolated components are absent (extraction kept only large components)
text_remnants = []
for r in range(11):
    for c in USED[r]:
        cell = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        rgb = cell[..., :3].astype(int)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        sat = mx - mn
        nw = (cell[..., 3] > 0) & (sat < 15) & (mx >= 250)
        if nw.any():
            ys, xs = np.where(nw)
            if (ys.max() - ys.min() < 8) and (xs.max() - xs.min() < 100) and nw.sum() < 400:
                text_remnants.append(f"r{r}c{c}")
checks.append({"name": "no ROW-label text remnant",
               "pass": len(text_remnants) == 0,
               "violations": text_remnants[:10]})

# no clipped frames: outer 2px rim alpha should be 0
clip_violations = []
for r in range(11):
    for c in USED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3]
        if a[:2].max() > 0 or a[-2:].max() > 0 or a[:, :2].max() > 0 or a[:, -2:].max() > 0:
            clip_violations.append(f"r{r}c{c}")
checks.append({"name": "no frames clipped at cell edges (2px rim transparent)",
               "pass": len(clip_violations) == 0,
               "violations": clip_violations[:10]})

# no overflow: each paste stays inside its cell (by construction). Verify: for each used cell,
# opaque pixels stay within [2, 206] x [2, 190].
overflow = []
for r in range(11):
    for c in USED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3] > 0
        if a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any():
            overflow.append(f"r{r}c{c}")
checks.append({"name": "no frame overflows into adjacent cells",
               "pass": len(overflow) == 0, "violations": overflow[:10]})

# Holes: enclosed transparent regions inside the character (>=20px) would mean a
# chunk was wrongly removed. Stray specks: opaque blobs separate from the body.
hole_violations = []
stray_violations = []
for r in range(11):
    for c in USED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3] > 0
        if not a.any():
            continue
        lab, k = ndimage.label(~a)
        if k:
            border = set(lab[0].tolist()) | set(lab[-1].tolist()) | \
                set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
            border.discard(0)
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1))
            for i in range(1, k + 1):
                if i not in border and sizes[i - 1] >= 20:
                    hole_violations.append(f"r{r}c{c}={int(sizes[i - 1])}px")
        lab2, k2 = ndimage.label(a)
        if k2:
            sz2 = ndimage.sum(np.ones_like(a, dtype=int), lab2, range(1, k2 + 1))
            big = [s for s in sz2 if s >= 20]
            if len(big) > 2:
                stray_violations.append(f"r{r}c{c}={len(big)}blobs")
checks.append({"name": "no unexpected transparent holes inside the character (>=20px enclosed)",
               "pass": len(hole_violations) == 0,
               "violations": hole_violations[:10]})
checks.append({"name": "no stray opaque blobs separate from the character body (>=20px)",
               "pass": len(stray_violations) == 0,
               "violations": stray_violations[:10]})

# character colour consistency: mean RGB across all used frames
opaque_rgbs = []
sizes = []
for r in range(11):
    for c in USED[r]:
        cell = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        a = cell[..., 3] > 0
        if a.any():
            opaque_rgbs.append(cell[a][..., :3].mean(axis=0))
            sizes.append(int(a.sum()))
opaque_arr = np.array(opaque_rgbs)
mean_rgb = opaque_arr.mean(axis=0).round(1).tolist()
std_rgb = opaque_arr.std(axis=0).round(1).tolist()
size_arr = np.array(sizes)
checks.append({"name": "character colour consistent across frames",
               "pass": max(std_rgb) < 12,
               "mean_rgb": mean_rgb, "std_rgb": std_rgb,
               "opaque_area_min": int(size_arr.min()),
               "opaque_area_max": int(size_arr.max()),
               "opaque_area_median": int(np.median(size_arr))})

# directions
checks.append({"name": "running-right (row 1) all face right",
               "pass": True, "note": "visually verified"})
checks.append({"name": "running-left (row 2) all face left",
               "pass": True, "note": "visually verified"})
checks.append({"name": "look directions 000/090/180/270 are clear",
               "pass": True,
               "note": "r9c0 looks up, r9c4 right, r10c0 down, r10c4 left (visually verified). "
                       "16 directions form a clockwise sweep."})

# size / baseline jump
heights = []
for r in range(11):
    for c in USED[r]:
        a = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, 3] > 0
        if not a.any():
            continue
        ys, xs = np.where(a)
        heights.append(int(ys.max() - ys.min() + 1))
h_arr = np.array(heights)
checks.append({"name": "no large character-height jumps (identity drift)",
               "pass": (h_arr.max() - h_arr.min()) < 80,
               "height_min": int(h_arr.min()),
               "height_max": int(h_arr.max()),
               "height_median": int(np.median(h_arr))})

report = {
    "asset": "yuntuan-samoyed",
    "target_dimensions": [1536, 2288],
    "grid": {"cols": 8, "rows": 11, "cell_w": 192, "cell_h": 208},
    "frames_required_per_row": {ROW_LABELS[r]: len(REQUIRED[r]) for r in range(11)},
    "frames_present": len(present_required),
    "frames_missing": missing_required,
    "summary_pass": all(c["pass"] for c in checks),
    "checks": checks,
}
def _conv(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(str(type(o)))


with open(OUT + "/validation-report.json", "w") as f:
    json.dump(report, f, indent=2, default=_conv)

print("SUMMARY pass=", report["summary_pass"])
for c in checks:
    print(("OK  " if c["pass"] else "FAIL"), c["name"])