"""Fill the transparent area of each extracted cell with the nearest character colour.

Without this, LANCZOS resampling blends the character edge with the leftover
checkerboard-grey RGB of the transparent pixels and produces a grey halo.
"""

import glob

import numpy as np
from PIL import Image
from scipy import ndimage

CELLS = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/cells"

n = 0
for p in glob.glob(CELLS + "/r*c*.png"):
    a = np.array(Image.open(p).convert("RGBA"))
    fg = a[..., 3] > 0
    if not fg.any() or fg.all():
        continue
    _, (ii, jj) = ndimage.distance_transform_edt(~fg, return_indices=True)
    nearest = a[..., :3][ii, jj]
    a[..., :3] = np.where(fg[..., None], a[..., :3], nearest)
    Image.fromarray(a, "RGBA").save(p)
    n += 1
print("decontaminated cells:", n)