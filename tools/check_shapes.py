#!/usr/bin/env python3
"""Check the shaping of a built font with hb-shape.

Usage: check_shapes.py FONT.ttf BASELINE.txt
BASELINE.txt is a shape-*.txt written by shape_tests.py for an earlier build: every case in it
must shape to the same glyphs and positions. The cases for the gemination mark, pluta and
dotted circle are checked on their own terms below.
"""
import re, sys, subprocess

font, baseline = sys.argv[1:3]
def shape(cps):
    u = ",".join("U+" + c for c in cps.split())
    return subprocess.run(["hb-shape", "--font-file", font, "--unicodes", u], capture_output=True, text=True, check=True).stdout.strip()

fails, n = [], 0
for line in open(baseline):
    if "[" not in line: continue
    cps = line[41:86].split("[")[0].strip(); want = line[line.index("["):].strip()
    n += 1
    if shape(cps) != want: fails.append(f"old case {cps}: got {shape(cps)}")
print(f"old cases: {n - len([f for f in fails if f.startswith('old')])}/{n} unchanged")

def glyphs(out): return re.findall(r"([\w.]+)=\d+(?:@(-?\d+),\d+)?\+(-?\d+)", out)
checks = [
    ("gemination after a consonant", "11392 113D2", [("k", None, "813"), ("u113D2", "-407", "0")]),
    ("gemination after a conjunct", "11392 113D0 113A1 113D2", [("k_A_t", None, "1255"), ("u113D2", "-625", "0")]),
    ("gemination before vowel sign u follows the kerned base", "11392 113D2 113BB", [("k", None, "461"), ("u113D2", "-55", "0"), ("u", None, "346")]),
    ("pluta after a vowel letter", "11380 113D3", [("u11380", None, "1329"), ("u113D3", None, "360")]),
    ("pluta after a vowel sign", "11392 113B8 113D3", [("k", None, "813"), ("a", None, "253"), ("u113D3", None, "360")]),
    ("lone gemination on the dotted circle", "113D2", [("uni25CC", None, "580"), ("u113D2", "-290", "0")]),
]
new_ok = 0
for label, cps, want in checks:
    got = [(g, x or None, a) for g, x, a in glyphs(shape(cps))]
    if got == want: new_ok += 1
    else: fails.append(f"{label}: got {got}, want {want}")
print(f"new cases: {new_ok}/{len(checks)}")
for f in fails: print("FAIL", f)
sys.exit(1 if fails else 0)
