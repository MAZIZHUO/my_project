import json
import os

import numpy as np
from PIL import Image

CELLS = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells"
OUTDIR = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
os.makedirs(OUTDIR, exist_ok=True)

meta = json.load(open(CELLS + "/meta.json"))

CW, CH, GW, GH = 192, 208, 1536, 2288
S = 0.96
BASE = 200

USED = {
    0: list(range(5)),
    1: list(range(8)),
    2: list(range(8)),
    3: list(range(4)),
    4: list(range(5)),
    5: list(range(8)),
    6: list(range(6)),
    7: list(range(6)),
    8: list(range(5)),
    9: list(range(8)),
    10: list(range(8)),
}

row_ground = {}
for r in range(11):
    bs = []
    for c in range(8):
        info = meta[str(r)][c]
        if info:
            bs.append(info["bbox_cell"][1] + info["bbox_cell"][3])
    if bs:
        row_ground[r] = float(np.median(bs))
print("row_ground:", {k: round(v, 1) for k, v in row_ground.items()})

canvas = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
placed = 0
for r in range(11):
    rg = row_ground[r]
    for c in USED[r]:
        info = meta[str(r)][c]
        if info is None:
            continue
        p = f"{CELLS}/r{r}c{c}.png"
        im = Image.open(p).convert("RGBA")
        bw, bh = im.size
        sw, sh = max(1, int(round(bw * S))), max(1, int(round(bh * S)))
        scaled = im.resize((sw, sh), Image.LANCZOS)
        bx0, by0, bw_, bh_ = info["bbox_cell"]
        src_top_rel = by0
        top_y = BASE + (src_top_rel - rg) * S
        left_x = (CW - sw) // 2
        px = c * CW + left_x
        py = int(round(r * CH + top_y))
        layer = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
        layer.paste(scaled, (px, py))
        canvas = Image.alpha_composite(canvas, layer)
        placed += 1
print("placed frames:", placed)

# drop LANCZOS ringing specks (isolated near-zero alpha) so every cell is clean
out = np.array(canvas)
out[..., 3] = np.where(out[..., 3] < 10, 0, out[..., 3])
canvas = Image.fromarray(out, "RGBA")

canvas.save(OUTDIR + "/spritesheet.png")
canvas.save(OUTDIR + "/spritesheet.webp", lossless=True)
print("saved spritesheet.png + spritesheet.webp", canvas.size)

bg = Image.new("RGBA", (GW, GH), (42, 45, 54, 255))
Image.alpha_composite(bg, canvas).save(OUTDIR + "/contact-sheet.png")
print("saved contact-sheet.png")