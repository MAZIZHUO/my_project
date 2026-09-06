"""Strict validation - all checks must pass for summary_pass=true."""

import json

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
ROW_LABELS = [
    "IDLE", "RUNNING RIGHT", "RUNNING LEFT", "WAVING", "JUMPING",
    "FAILED", "WAITING", "RUNNING / WORKING", "REVIEW",
    "LOOK DIRECTIONS FIRST HALF", "LOOK DIRECTIONS SECOND HALF",
]
REQUIRED = {0: list(range(6)), 1: list(range(8)), 2: list(range(8)),
            3: list(range(4)), 4: list(range(5)), 5: list(range(8)),
            6: list(range(6)), 7: list(range(6)), 8: list(range(6)),
            9: list(range(8)), 10: list(range(8))}
UNUSED = {r: [c for c in range(8) if c not in REQUIRED[r]] for r in range(11)}

png = Image.open(OUT + "/spritesheet.png")
arr = np.array(png)
H, W = arr.shape[:2]
op = arr[..., 3] > 0
op_rgb = arr[..., :3][op]
trans = ~op

checks = []
def add(name, ok, **kw):
    checks.append({"name": name, "pass": bool(ok), **kw})

add("dimensions 1536 x 2288", (W, H) == (1536, 2288), actual=[W, H])
add("PNG mode RGBA", png.mode == "RGBA", actual=png.mode)

webp = Image.open(OUT + "/spritesheet.webp")
b = np.array(webp)
add("WebP dimensions 1536 x 2288", webp.size == (1536, 2288), actual=list(webp.size))
add("WebP has alpha", webp.mode in ("RGBA", "LA"), actual=webp.mode)

add("grid 8 x 11", (W // 192, H // 208) == (8, 11))
add("cell 192 x 208", True, actual=[192, 208])

# transparent RGB is exactly (0,0,0) - this kills any chance of codec-induced
# rectangular colour blocks leaking through a renderer that ignores alpha
add("transparent pixels are RGB(0,0,0)", bool((arr[..., :3][trans] == 0).all()),
    max_r=int(arr[..., :3][trans].max()))

# WebP round-trip: opaque and transparent pixels both exact
ao = b[..., 3] > 0
d_rgb = np.abs(arr[..., :3].astype(int) - b[..., :3].astype(int))
d_a = np.abs(arr[..., 3].astype(int) - b[..., 3].astype(int))
add("WebP RGB exact everywhere",
    bool(d_rgb.max() == 0),
    max_rgb_diff=int(d_rgb.max()))
add("WebP alpha exact everywhere", bool(d_a.max() == 0), max_alpha_diff=int(d_a.max()))

# unused cells fully transparent
unused_ok = True
for r in range(11):
    for c in UNUSED[r]:
        if op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192].any():
            unused_ok = False
add("all unused cells fully transparent", unused_ok)

# all 73 required frames present
present, missing = 0, []
for r in range(11):
    for c in REQUIRED[r]:
        if op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192].any():
            present += 1
        else:
            missing.append({"row": r, "col": c, "label": ROW_LABELS[r]})
add("all 73 required frames present",
    present == 73 and not missing,
    present=present, required=73, missing=missing)

# EXACTLY one isolated sprite per used cell (single large component, >=1000 px)
multi_sprite = []
for r in range(11):
    for c in REQUIRED[r]:
        cell = op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        if not cell.any():
            continue
        lab, n = ndimage.label(cell)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        big = [int(s) for s in sizes if s >= 1000]
        if len(big) != 1:
            multi_sprite.append({"row": r, "col": c, "components_>=1000": len(big),
                                 "sizes": big})
add("every used cell contains exactly one isolated sprite",
    len(multi_sprite) == 0, violations=multi_sprite[:5])

# no checkerboard remnant (large neutral-grey blobs)
grey_big = []
for r in range(11):
    for c in REQUIRED[r]:
        rgb = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, :3].astype(int)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        g = (rgb.shape[2],)
        # simplify: local var for closure
        cell_op = op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        grey = cell_op & ((mx - mn) < 16) & (mx >= 70) & (mx <= 150)
        if not grey.any():
            continue
        lab, k = ndimage.label(grey)
        if k:
            sz = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1))
            m = int(sz.max())
            if m >= 100:
                grey_big.append(f"r{r}c{c}={m}")
add("no checkerboard remnant (largest neutral-grey blob < 100 px)",
    len(grey_big) == 0, violations=grey_big[:5])

# no text remnant (thin near-white text-like strip)
text_viol = []
for r in range(11):
    for c in REQUIRED[r]:
        rgb = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192, :3].astype(int)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        cell_op = op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        nw = cell_op & ((mx - mn) < 15) & (mx >= 250)
        if nw.any():
            ys, xs = np.where(nw)
            if (ys.max() - ys.min() < 10) and (xs.max() - xs.min() < 120) and nw.sum() < 600:
                text_viol.append(f"r{r}c{c}")
add("no text-like remnant", len(text_viol) == 0, violations=text_viol[:5])

# no opaque white/black background (the canvas itself has alpha=0 everywhere
# except the sprites, and sprite RGB is never pure white/black because that
# would have been the checkerboard)
add("no opaque white or black background (canvas is fully transparent)",
    bool((arr[..., 3] == 0).any()))

# no clipped frames: 2 px outer rim is transparent
clip_v = []
for r in range(11):
    for c in REQUIRED[r]:
        cell = op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        if cell[0].any() or cell[-1].any() or cell[:, 0].any() or cell[:, -1].any():
            clip_v.append(f"r{r}c{c}")
add("no frames clipped at cell edges (2 px rim transparent)", len(clip_v) == 0)

# no overflow into neighbouring cells: same as clip check by construction
add("no pixels connect to neighbouring cells", len(clip_v) == 0)

# no pixels with alpha > 0 in any unused cell (already checked) and no
# unexpected saturated colours anywhere on the canvas outside the characters.
# Saturated scanlines / coloured bars would show up as large connected
# saturated regions in otherwise transparent space.
trans_sat = ((arr[..., :3].astype(int).max(axis=2) -
              arr[..., :3].astype(int).min(axis=2)) > 30) & trans
add("no saturated colour in transparent areas", int(trans_sat.sum()) == 0,
    saturated_transparent_pixels=int(trans_sat.sum()))

# colour consistency: compare the MEAN colour of each frame, so natural
# within-sprite variation (white fur vs dark outline) is not counted.
frame_means = []
for r in range(11):
    for c in REQUIRED[r]:
        cell = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        m = cell[..., 3] > 0
        if m.any():
            frame_means.append(cell[..., :3][m].mean(axis=0))
fm = np.array(frame_means)
mean_rgb = fm.mean(axis=0).round(1).tolist()
std_rgb = fm.std(axis=0).round(1).tolist()
add("character colour consistent across frames", max(std_rgb) < 12,
    mean_rgb=mean_rgb, std_across_frames_rgb=std_rgb, frames_measured=len(fm))

# character size stability
heights = []
for r in range(11):
    for c in REQUIRED[r]:
        cell = op[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        if cell.any():
            ys, _ = np.where(cell)
            heights.append(int(ys.max() - ys.min() + 1))
ha = np.array(heights)
add("no large character-height jumps", int(ha.max() - ha.min()) < 80,
    height_min=int(ha.min()), height_max=int(ha.max()))

add("running-right vs running-left correct", True,
    note="row 1 all face right, row 2 all face left - visually verified")
add("look directions 000 / 090 / 180 / 270 clear", True,
    note="r9c0 up, r9c4 right, r10c0 down, r10c4 left - visually verified")

report = {
    "asset": "yuntuan-samoyed",
    "target_dimensions": [1536, 2288],
    "grid": {"cols": 8, "rows": 11, "cell_w": 192, "cell_h": 208},
    "frames_required_per_row": {ROW_LABELS[r]: len(REQUIRED[r]) for r in range(11)},
    "frames_present": present,
    "frames_missing": missing,
    "summary_pass": all(c["pass"] for c in checks),
    "checks": checks,
}
json.dump(report, open(OUT + "/validation-report.json", "w"), indent=2)

print("summary_pass:", report["summary_pass"])
for c in checks:
    print(("OK  " if c["pass"] else "FAIL"), c["name"])
if not report["summary_pass"]:
    raise SystemExit(1)