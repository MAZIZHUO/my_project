import numpy as np
from PIL import Image

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"

arr = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = arr.shape
mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn
val = mx

# checkerboard = neutral grey in the two detected levels
gray = (sat < 16) & (val >= 70) & (val <= 150)
fg = ~gray
print("fg fraction:", round(float(fg.mean()), 4))


def runs(mask, minlen=1):
    """Return (start, end) of True runs."""
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    return [(int(a), int(b)) for a, b in zip(st, en) if b - a >= minlen]


rowprof = fg.mean(axis=1)
bands = runs(rowprof > 0.02, minlen=60)
print("bands found:", len(bands))
for i, (a, b) in enumerate(bands):
    print("  band", i, "y", a, b, "h", b - a)

colprof = fg.mean(axis=0)
cols = runs(colprof > 0.03, minlen=40)
print("cols found:", len(cols))
for i, (a, b) in enumerate(cols):
    print("  col", i, "x", a, b, "w", b - a)
