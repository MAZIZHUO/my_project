import numpy as np
from PIL import Image

SRC = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"

im = Image.open(SRC).convert("RGB")
arr = np.array(im).astype(np.int16)
H, W, _ = arr.shape
print("size =", W, "x", H, "mode =", im.mode)

mx = arr.max(axis=2)
mn = arr.min(axis=2)
sat = mx - mn
val = mx

gray = (sat < 18) & (val > 60) & (val < 235)
print("overall gray frac =", round(float(gray.mean()), 3))

non_gray_row = 1.0 - gray.mean(axis=1)
print("row profile every 20px:")
for y in range(0, H, 20):
    f = float(non_gray_row[y:y + 20].mean())
    print(y, round(f, 3), "#" * int(f * 50))
