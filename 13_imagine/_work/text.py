import numpy as np
from PIL import Image

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"

arr = np.array(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = arr.shape
mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn

near_white = (sat < 15) & (mx >= 240)
prof = near_white.mean(axis=1)
print("near-white row profile (every 8px), W =", W)
for y in range(0, H, 8):
    f = float(prof[y:y + 8].mean())
    n = int(f * W * 8)
    print(f"{y:5d} {n:6d} " + "#" * min(60, n // 8))
