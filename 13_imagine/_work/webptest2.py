import os

import numpy as np
from PIL import Image

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
TMP = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work"

src = Image.open(OUT + "/spritesheet.png").convert("RGBA")
a = np.array(src).astype(np.int16)

variants = {
    "lossless_default": dict(lossless=True),
    "lossless_method0": dict(lossless=True, method=0),
    "lossless_method6": dict(lossless=True, method=6),
    "lossless_q100": dict(lossless=True, quality=100),
    "lossy_q100": dict(quality=100),
    "lossy_q95": dict(quality=95),
    "lossy_q90_m6": dict(quality=90, method=6),
}
for name, kw in variants.items():
    p = os.path.join(TMP, f"v_{name}.webp")
    try:
        src.save(p, **kw)
        rt = np.array(Image.open(p).convert("RGBA")).astype(np.int16)
        d = np.abs(a - rt)
        print(f"{name:18s} size={os.path.getsize(p):>9,}  maxdiff={int(d.max()):>3}  "
              f"meandiff={d.mean():8.4f}  alpha_ok={bool((rt[..., 3] == a[..., 3]).all())}")
    except Exception as e:
        print(f"{name:18s} ERROR {e}")

# inspect the "red" pixels of the PNG
rgb = a[..., :3]
mx = rgb.max(axis=2)
mn = rgb.min(axis=2)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
op = a[..., 3] > 0
red = op & (sat > 0.35) & (rgb[..., 0] > rgb[..., 1] + 25) & (rgb[..., 0] > rgb[..., 2] + 25)
ys, xs = np.where(red[0:208, 0:192])
print("\nr0c0 red pixel count:", len(ys))
if len(ys):
    print("  y range:", ys.min(), ys.max(), " x range:", xs.min(), xs.max())
    for i in range(0, min(len(ys), 12), max(1, len(ys) // 12)):
        y, x = ys[i], xs[i]
        print(f"   at (y={y}, x={x}) rgb={tuple(int(v) for v in rgb[y, x])} alpha={int(a[y, x, 3])}")
