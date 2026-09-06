import json
import os

import numpy as np
from PIL import Image

CELLS = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells"
OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work"

meta = json.load(open(CELLS + "/meta.json"))
CW, CH = 150, 165
sheet = np.zeros((11 * CH, 8 * CW, 3), np.uint8)
sheet[:] = (28, 30, 38)

for r in range(11):
    row_info = meta[str(r)]
    for c in range(8):
        info = row_info[c]
        if info is None:
            continue
        p = f"{CELLS}/r{r}c{c}.png"
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        s = min((CW - 6) / w, (CH - 6) / h)
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        a = np.array(im)
        rgb = a[..., :3].astype(float)
        al = a[..., 3:4].astype(float) / 255.0
        y = r * CH + (CH - im.size[1]) // 2
        x = c * CW + (CW - im.size[0]) // 2
        dst = sheet[y:y + im.size[1], x:x + im.size[0]].astype(float)
        sheet[y:y + im.size[1], x:x + im.size[0]] = (
            rgb * al + dst * (1 - al)).astype(np.uint8)

Image.fromarray(sheet).save(OUT + "/preview_extract.png")
print("saved preview_extract.png", sheet.shape)

for r in range(11):
    infos = [v for v in meta[str(r)] if v]
    print(f"row {r}: " + " | ".join(
        f"c{v['col']}({v['bbox_src'][0]},{v['bbox_src'][1]})"
        f"{v['bbox_src'][2]}x{v['bbox_src'][3]}" for v in infos))
