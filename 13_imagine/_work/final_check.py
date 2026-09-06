import json
import os

from PIL import Image

OUT = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/yuntuan_pet_output"
REQUIRED = ["spritesheet.png", "spritesheet.webp", "pet.json",
            "contact-sheet.png", "validation-report.json", "README.md"]
EXTRA = ["preview-black.png"]

ok = True
for f in REQUIRED + EXTRA:
    p = os.path.join(OUT, f)
    if os.path.exists(p):
        print(f"OK   {p}  ({os.path.getsize(p):,} bytes)")
    else:
        print(f"MISS {p}")
        if f in REQUIRED:
            ok = False

print()
for f in ("spritesheet.png", "spritesheet.webp", "contact-sheet.png", "preview-black.png"):
    im = Image.open(os.path.join(OUT, f))
    print(f"{f:22s} size={im.size} mode={im.mode}")

rep = json.load(open(os.path.join(OUT, "validation-report.json")))
print("\nsummary_pass =", rep["summary_pass"])
print("frames_present =", rep["frames_present"], " missing =", rep["frames_missing"])
print("checks failed  =", [c["name"] for c in rep["checks"] if not c["pass"]])
print("\npet.json:", open(os.path.join(OUT, "pet.json")).read().strip().replace("\n", " "))

src = r"c:/Users/hp/Desktop/Python_Projects/my_project/13_imagine/Gemini_Generated_Image_8ey5zg8ey5zg8ey5.jpg"
print("\nsource untouched:", os.path.exists(src), f"{os.path.getsize(src):,} bytes")
