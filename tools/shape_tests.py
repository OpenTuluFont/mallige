#!/usr/bin/env python3
"""Shape a fixed list of Tulu-Tigalari test strings with hb-shape and render them with hb-view.

Usage: shape_tests.py OUTDIR FONT.ttf [FONT2.ttf ...]
Writes OUTDIR/shape-<font>.txt (glyph names and positions per case) and OUTDIR/sheet.png
(one row per case, one column per font, labelled), so a before/after comparison is one image.
Needs hb-shape and hb-view (HarfBuzz) and Pillow.
"""
import sys, os, subprocess, unicodedata
from PIL import Image, ImageDraw, ImageFont

CASES = [
    ("tulu  ta+u la+u",             "113A1 113BB 113AD 113BB"),
    ("kta  ka conj ta",             "11392 113D0 113A1"),
    ("kka  ka conj ka",             "11392 113D0 11392"),
    ("nnkta  nna conj ka conj ta",  "113A0 113D0 11392 113D0 113A1"),
    ("k+virama",                    "11392 113CE"),
    ("kta+virama",                  "11392 113D0 113A1 113CE"),
    ("kee  ka + sign ee",           "11392 113C2"),
    ("koo  ka + sign oo",           "11392 113C7"),
    ("kau  ka + sign au",           "11392 113C8"),
    ("kai  ka + sign ai",           "11392 113C5"),
    ("kaa ki kii",                  "11392 113B8 0020 11392 113B9 0020 11392 113BA"),
    ("ku kuu",                      "11392 113BB 0020 11392 113BC"),
    ("lu  (no precomposed form)",   "113AD 113BB"),
    ("ktu  cluster + u",            "11392 113D0 113A1 113BB"),
    ("rya  repha ya",               "113D1 113AB"),
    ("ryu  repha ya u",             "113D1 113AB 113BB"),
    ("rmma  repha ma conj ma",      "113D1 113AA 113D0 113AA"),
    ("rkya  repha ka conj ya",      "113D1 11392 113D0 113AB"),
    ("kkha  ka conj kha (single subjoined)", "11392 113D0 11393"),
    ("shrii  sha conj ra ii",       "113AF 113D0 113AC 113BA"),
    ("kam kah  anusvara visarga",   "11392 113CC 0020 11392 113CD"),
    ("k + candra anunasika",        "11392 113CA"),
    ("ka danda double-danda",       "11392 113D4 0020 113D5"),
    ("k conj rra  (no rule: fallback)", "11392 113D0 113B4"),
    ("e ee ai o oo au  (letters)",  "1138A 1138B 1138E 1138F 11390 11391"),
    # added with the gemination mark, pluta and dotted circle (v1.6)
    ("kka  ka + gemination mark",   "11392 113D2"),
    ("ktta  kta + gemination mark", "11392 113D0 113A1 113D2"),
    ("kkau  ka + gemination + u",   "11392 113D2 113BB"),
    ("a + pluta  (vowel letter)",   "11380 113D3"),
    ("kaa + pluta",                 "11392 113B8 113D3"),
    ("lone gemination: dotted circle", "113D2"),
    ("lone pluta",                  "113D3"),
]

out = sys.argv[1]; fonts = sys.argv[2:]
os.makedirs(out, exist_ok=True)
def uplus(s): return ",".join("U+" + c for c in s.split())
cells = {}
for fp in fonts:
    tag = os.path.splitext(os.path.basename(fp))[0]
    lines = []
    for label, cps in CASES:
        r = subprocess.run(["hb-shape", "--font-file", fp, "--unicodes", uplus(cps)], capture_output=True, text=True)
        lines.append(f"{label:40} {cps:45} {r.stdout.strip()}")
        os.makedirs(os.path.join(out, "cells"), exist_ok=True); png = os.path.join(out, "cells", f"{tag}-{len(lines):02d}.png")
        subprocess.run(["hb-view", "--font-file", fp, "--unicodes", uplus(cps), "-o", png,
                        "--font-size", "56", "--margin", "8", "--background", "#FFFFFF", "--foreground", "#000000"], check=True)
        cells[(tag, label)] = png
    open(os.path.join(out, f"shape-{tag}.txt"), "w").write("\n".join(lines) + "\n")
    print(f"{tag}: {len(lines)} cases -> shape-{tag}.txt")

# sheet
tags = [os.path.splitext(os.path.basename(fp))[0] for fp in fonts]
colw, labw, rowh = 520, 300, 120
W = labw + colw * len(tags); H = rowh * (len(CASES) + 1)
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
try: fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
except Exception: fnt = ImageFont.load_default()
for j, t in enumerate(tags): d.text((labw + j * colw + 10, 10), t, fill="black", font=fnt)
for i, (label, cps) in enumerate(CASES):
    y = rowh * (i + 1)
    d.line([(0, y), (W, y)], fill="#ddd")
    d.text((10, y + 10), label, fill="black", font=fnt); d.text((10, y + 34), cps, fill="#06c", font=fnt)
    for j, t in enumerate(tags):
        c = Image.open(cells[(t, label)]).convert("RGB")
        if c.width > colw - 20 or c.height > rowh - 10:
            c.thumbnail((colw - 20, rowh - 10))
        img.paste(c, (labw + j * colw + 10, y + 5))
img.save(os.path.join(out, "sheet.png")); print("sheet:", os.path.join(out, "sheet.png"))

# browser test page: same cases, one column per font, for tools/browser_shots.mjs
faces = "\n".join(f'@font-face {{ font-family: "{t}"; src: url("{os.path.relpath(fp, out)}"); }}' for t, fp in zip(tags, fonts))
rows = []
for label, cps in CASES:
    text = "".join(chr(int(c, 16)) for c in cps.split())
    rows.append(f"<tr><th>{label}<br><small>{cps}</small></th>" +
                "".join(f'<td lang="tcy-Tutg" style="font-family:\'{t}\'">{text}</td>' for t in tags) + "</tr>")
html = f"""<!doctype html><meta charset="utf-8"><title>mallige tutg shaping tests</title>
<style>{faces}
body {{ font-family: Helvetica, Arial, sans-serif; margin: 20px; }} th {{ text-align: left; font-weight: normal; width: 300px; padding: 6px; }}
small {{ color: #06c; }} td {{ font-size: 44px; padding: 6px 16px; }} tr {{ border-top: 1px solid #ddd; }} table {{ border-collapse: collapse; }}
</style><table><tr><th></th>{"".join(f"<td style='font-size:16px'>{t}</td>" for t in tags)}</tr>{"".join(rows)}</table>
<p id="ua" style="font-size:12px;color:#666"></p><script>document.getElementById("ua").textContent = navigator.userAgent</script>"""
open(os.path.join(out, "test.html"), "w").write(html); print("page:", os.path.join(out, "test.html"))
