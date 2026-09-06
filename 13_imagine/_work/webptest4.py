import os

import numpy as np
from PIL import Image

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
TMP = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work"

a = np.array(Image.open(OUT + "/spritesheet.png").convert("RGBA")).astype(np.int16)
op = a[..., 3] > 0

z = a.copy()
z[~op] = 0
zimg = Image.fromarray(z.astype(np.uint8), "RGBA")
src = Image.fromarray(a.astype(np.uint8), "RGBA")

for name, img, basis in [("m0_keep", src, a), ("m4_keep", src, a),
                         ("m0_zero", zimg, z), ("m4_zero", zimg, z)]:
    kw = dict(lossless=True, method=0 if "m0" in name else 4)
    p = os.path.join(TMP, f"w_{name}.webp")
    img.save(p, **kw)
    rt = np.array(Image.open(p).convert("RGBA")).astype(np.int16)
    d = np.abs(basis[..., :3] - rt[..., :3]).max(axis=2)
    dt = d[~op]
    print(f"{name:9s} size={os.path.getsize(p):>9,}  "
          f"transparentRGB: max={int(dt.max())} mean={dt.mean():7.3f} "
          f"nbad(>16)={int((dt > 16).sum()):>8}  alpha_exact={bool((rt[..., 3] == a[..., 3]).all())}")
