import numpy as np
from PIL import Image

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"
OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work"

arr = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = arr.shape
mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn

near_white = (sat < 15) & (mx >= 240)
prof = near_white.mean(axis=1)


def runs(mask, minlen=1, maxlen=10**9):
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    return [(int(a), int(b)) for a, b in zip(st, en) if minlen <= b - a <= maxlen]


# thin isolated near-white runs == text strips
text_runs = runs(prof > 0.006, minlen=8, maxlen=70)
print("candidate text strips:", len(text_runs))
for a, b in text_runs:
    print("   y", a, "-", b, " h", b - a)

# save a crop covering rows 3-4 boundary for visual check
crop = arr[700:1220, 0:600]
Image.fromarray(crop.astype(np.uint8)).save(OUT + "/crop_r3_r4.png")
print("saved crop_r3_r4.png", crop.shape)
