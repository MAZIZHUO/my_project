import os

import numpy as np
from PIL import Image

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
TMP = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work"

src = Image.open(OUT + "/spritesheet.png").convert("RGBA")
a = np.array(src).astype(np.int16)
alpha = a[..., 3]
op = alpha > 0

# variant: zero RGB wherever alpha == 0 (standard, avoids any transparent-RGB ambiguity)
z = a.copy()
z[~op] = 0
zimg = Image.fromarray(z.astype(np.uint8), "RGBA")

tests = [
    ("lossless_m4", src, dict(lossless=True)),
    ("lossless_m0", src, dict(lossless=True, method=0)),
    ("lossless_m1", src, dict(lossless=True, method=1)),
    ("lossless_m2", src, dict(lossless=True, method=2)),
    ("lossless_m3", src, dict(lossless=True, method=3)),
    ("zero_lossless_m4", zimg, dict(lossless=True)),
    ("zero_lossless_m6", zimg, dict(lossless=True, method=6)),
]

for name, img, kw in tests:
    p = os.path.join(TMP, f"t_{name}.webp")
    img.save(p, **kw)
    rt = np.array(Image.open(p).convert("RGBA")).astype(np.int16)
    d = np.abs(a[..., :3] - rt[..., :3]).max(axis=2)
    dao = d[op]
    dat = d[~op]
    alpha_exact = bool((rt[..., 3] == alpha).all())
    print(f"{name:18s} size={os.path.getsize(p):>9,}  "
          f"opaque: max={int(dao.max()) if dao.size else 0} mean={dao.mean():6.3f} nbad={int((dao > 8).sum()):>7} | "
          f"alpha_exact={alpha_exact}")
