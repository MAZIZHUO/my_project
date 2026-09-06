import numpy as np
from PIL import Image
import PIL

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
print("Pillow version:", PIL.__version__)
print("WebP support:", "webp" in Image.registered_extensions().values() or True)

src = Image.open(OUT + "/spritesheet.png").convert("RGBA")
a = np.array(src).astype(np.int16)

# round-trip: save the PNG out as lossless webp and read back
src.save(r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/rt.webp", lossless=True)
rt = np.array(Image.open(r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/_work/rt.webp").convert("RGBA")).astype(np.int16)
print("round-trip lossless webp: max diff", int(np.abs(a - rt).max()),
      "mean diff", round(float(np.abs(a - rt).mean()), 4))

# where does the existing webp differ?
b = np.array(Image.open(OUT + "/spritesheet.webp").convert("RGBA")).astype(np.int16)
diff = np.abs(a - b).max(axis=2)
print("\nexisting webp differs from png in", int((diff > 8).sum()), "pixels")
ys, xs = np.where(diff > 8)
if len(ys):
    print("diff bbox: y", ys.min(), ys.max(), " x", xs.min(), xs.max())
    # which rows/cols of the grid
    print("grid rows affected:", sorted(set((ys // 208).tolist()))[:15])
    print("grid cols affected:", sorted(set((xs // 192).tolist()))[:15])

# localise saturated red pixels in the PNG
rgb = a[..., :3]
mx = rgb.max(axis=2).astype(float)
mn = rgb.min(axis=2).astype(float)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
op = a[..., 3] > 0
red = op & (sat > 0.35) & (rgb[..., 0] > rgb[..., 1] + 25) & (rgb[..., 0] > rgb[..., 2] + 25)
print("\nPNG red-ish opaque pixels:", int(red.sum()))
USED = {0: range(5), 1: range(8), 2: range(8), 3: range(4), 4: range(5),
        5: range(8), 6: range(6), 7: range(6), 8: range(5), 9: range(8), 10: range(8)}
counts = []
for r in range(11):
    for c in USED[r]:
        n = int(red[r * 208:(r + 1) * 208, c * 192:(c + 1) * 192].sum())
        if n:
            counts.append((n, r, c))
counts.sort(reverse=True)
print("top cells by red pixels:", counts[:8])
print("cells with red:", len(counts))
