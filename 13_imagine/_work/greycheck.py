import numpy as np
from PIL import Image
from scipy import ndimage

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
arr = np.array(Image.open(OUT + "/spritesheet.png").convert("RGBA"))

USED = {0: range(5), 1: range(8), 2: range(8), 3: range(4), 4: range(5),
        5: range(8), 6: range(6), 7: range(6), 8: range(5), 9: range(8), 10: range(8)}

worst = []
for r in range(11):
    for c in USED[r]:
        cell = arr[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192]
        a = cell[..., 3]
        rgb = cell[..., :3].astype(int)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        grey = (a > 0) & ((mx - mn) < 16) & (mx >= 70) & (mx <= 150)
        n = int(grey.sum())
        if n == 0:
            continue
        lab, k = ndimage.label(grey)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1)) if k else [0]
        worst.append((int(max(sizes)), n, r, c))

worst.sort(reverse=True)
print("largest grey blob per cell (blob_px, total_grey_px, row, col):")
for w in worst[:12]:
    print("  ", w)
print("max grey blob overall:", worst[0][0] if worst else 0)
