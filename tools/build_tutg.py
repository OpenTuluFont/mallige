#!/usr/bin/env python3
"""Build the Tulu-Tigalari (`tutg`) OpenType layer for mallige.

Input : the font as shipped (XmlAlieg(mallige)v1.4.ttf), whose layout is a Latin keyboard
        hack: one `liga` lookup under DFLT/latn whose components are ASCII key glyphs
        ('A' = conjoiner key, 'X' = dead-consonant marker, 'f' = repha tick, 'u'/'U' =
        vowel signs U/UU), plus a `kern` table that pulls subjoined forms, signs, virama and
        repha back under or over the base.
Output: the same font with a `tutg` script whose Unicode Tulu-Tigalari text shapes through
        HarfBuzz's Universal Shaping Engine and renders like the keyboard layout:

  1. cmap  - Tulu-Tigalari code points whose keyboard glyph has the same outline point at
             the keyboard glyph (kerning and ligatures reference those names); the missing
             conjoiner, repha, danda and double danda are added.
  2. glyf  - new glyphs: conjoiner (empty), double danda (two of the keyboard's full-stop
             bar), gemination mark and pluta (drawn here after the Unicode 16 code chart,
             stroked to the weight of the font) and the dotted circle U+25CC. The repha is
             the keyboard's 'f' tick, the danda its full stop.
  3. GSUB  - script `tutg` (default language system):
             cjct : every keyboard ligature rule translated to Unicode input
                    ('A' -> CONJOINER, trailing 'A X' -> VIRAMA), one flat lookup, longest match
             abvs : repha forms, applied after the USE has moved the repha behind the base
             blws : repha form + vowel sign U/UU
             psts : a conjoiner that no rule consumed becomes the visible virama
  4. GPOS  - script `tutg` sharing the existing `kern` feature, plus `blwm`: the gemination
             mark (zero advance, GDEF mark) attaches centred under the consonant or cluster
             before it; an attachment, not a pair adjustment, so it follows the kerning of a
             vowel sign that comes after the mark.
  5. GDEF  - the new glyphs get a class.
The DFLT/latn keyboard layout is left untouched.

Usage: build_tutg.py IN.ttf OUT.ttf [--report REPORT.md]
"""
import re, copy, math, argparse
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.otlLib.builder import LigatureSubstBuilder, SingleSubstBuilder, MarkBasePosBuilder, buildAnchor
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--report")
ap.add_argument("--version", help="e.g. 1.5: sets head.fontRevision and the name-table version strings")
args = ap.parse_args()
font = TTFont(args.src)
glyf, hmtx, cmap = font["glyf"], font["hmtx"], font["cmap"]
report = []
def log(s): report.append(s); print(s)


# ---------------------------------------------------------------- drawn glyphs
STROKE = 76   # letter strokes run about 80, the danda bar is 72

def bezier(p0, p1, p2, p3, n):
    return [tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t**2*c + t**3*d for a, b, c, d in zip(p0, p1, p2, p3))
            for t in (i / n for i in range(n + 1))]

def stroked(path, width=STROKE, step=26):
    """Outline of a round-capped stroke along a polyline, as one closed contour of off-curve
    points (TrueType reads them as a smooth quadratic spline)."""
    pts = [path[0]]
    for q in path[1:]:
        d = math.dist(pts[-1], q)
        if d >= step * 0.6: pts.append(q)
    h = width / 2
    def normal(i):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        d = math.dist(a, b); return (-(b[1] - a[1]) / d, (b[0] - a[0]) / d)
    left = [(x + h * normal(i)[0], y + h * normal(i)[1]) for i, (x, y) in enumerate(pts)]
    right = [(x - h * normal(i)[0], y - h * normal(i)[1]) for i, (x, y) in enumerate(pts)]
    def cap(c, n, a_start):
        a0 = math.atan2(n[1], n[0]) + a_start
        return [(c[0] + h * math.cos(a0 - math.pi * k / 6), c[1] + h * math.sin(a0 - math.pi * k / 6)) for k in range(1, 6)]
    return left + cap(pts[-1], normal(len(pts) - 1), 0) + right[::-1] + cap(pts[0], normal(0), math.pi)

def draw_contours(contours):
    pen = TTGlyphPen(None)
    for c in contours:
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]))
        if area > 0: c = c[::-1]   # outer contours run clockwise
        pen.qCurveTo(*[(round(x), round(y)) for x, y in c], None); pen.closePath()
    return pen.glyph()

def circle_contour(cx, cy, r, n=8):
    k = r / math.cos(math.pi / n)
    return [(cx + k * math.cos(2 * math.pi * (i + .5) / n), cy + k * math.sin(2 * math.pi * (i + .5) / n)) for i in range(n)]

def pluta_glyph():
    # the "2"-like curl of the code chart: hook to the right, back to the left, long diagonal down
    s = 560 / 360
    def P(x, y): return ((x - 99) * s + 30, (425 - y) * s)
    segs = [((112, 98), (160, 75), (235, 65), (250, 105)), ((250, 105), (262, 150), (170, 175), (130, 210)),
            ((130, 210), (112, 225), (115, 240), (130, 262)), ((130, 262), (180, 320), (230, 365), (278, 415))]
    path = []
    for sg in segs: path += bezier(*[P(*p) for p in sg], 14)[:-1]
    path.append(P(*segs[-1][-1]))
    return draw_contours([stroked(path)]), 360

def gemination_glyph():
    # small arch below the consonant, centred on x = 0, zero advance
    rx, ry, cy = 92, 72, -150
    path = [(rx * math.cos(a), cy + ry * math.sin(a)) for a in (math.pi - math.pi * i / 24 for i in range(25))]
    return draw_contours([stroked(path)]), 0

def dotted_circle_glyph():
    r, cx, cy, dot = 215, 290, 275, 33
    return draw_contours([circle_contour(cx + r * math.cos(2 * math.pi * i / 12), cy + r * math.sin(2 * math.pi * i / 12), dot) for i in range(12)]), 580

# ---------------------------------------------------------------- 1. keyboard key -> code point
# Verified by outline identity (tools/match_hack.py) or by eye on the contact sheets.
KEY_TO_CP = {
    "k": 0x11392, "K": 0x11393, "g": 0x11394, "G": 0x11395, "Z": 0x11396,
    "c": 0x11397, "C": 0x11398, "j": 0x11399, "z": 0x1139B,
    "q": 0x1139C, "Q": 0x1139D, "w": 0x1139E, "W": 0x1139F, "N": 0x113A0,
    "t": 0x113A1, "T": 0x113A2, "d": 0x113A3, "D": 0x113A4, "n": 0x113A5,
    "p": 0x113A6, "P": 0x113A7, "b": 0x113A8, "B": 0x113A9, "m": 0x113AA,
    "y": 0x113AB, "r": 0x113AC, "l": 0x113AD, "v": 0x113AE,
    "S": 0x113AF, "x": 0x113B0, "s": 0x113B1, "h": 0x113B2, "L": 0x113B3,
    "a": 0x113B8,   # vowel sign AA (keyboard glyph is the kerned one)
    "u": 0x113BB, "U": 0x113BC,   # vowel signs U, UU: kern classes and precomposed forms use these
    "R": 0x113BD,   # vowel sign vocalic R
    "F": 0x113CA,   # candra anunasika, kerned under the base
    "M": 0x113CC, "H": 0x113CD,   # anusvara, visarga (identical outlines)
    "A": 0x113CE,   # visible virama (identical outline; kern class)
    "f": 0x113D1,   # REPHA = the keyboard tick (kern class pulls it over the base)
    "period": 0x113D4,   # DANDA = the keyboard's full stop, a full-height bar
}
# Code points that keep their own glyph (no keyboard twin or a deliberately different one):
# independent vowels, 1139A JHA (J.1), RRA, LLLA, avagraha, signs I/II/AI/EE/OO/AU/vocalic RR-LL,
# short e/o signs on unassigned 113C1/113C3/113C4/113C6, looped virama, pushpikas.

NEW = {  # code point -> (glyph name, source)
    0x113D0: ("u113D0", "empty"),          # CONJOINER
    0x113D5: ("u113D5", "dandadouble"),    # DOUBLE DANDA = two dandas
    0x113D2: ("u113D2", "gemination"),     # GEMINATION MARK, drawn
    0x113D3: ("u113D3", "pluta"),          # SIGN PLUTA, drawn
    0x25CC:  ("uni25CC", "dottedcircle"),  # DOTTED CIRCLE, drawn
}
DRAWN = {"gemination": gemination_glyph, "pluta": pluta_glyph, "dottedcircle": dotted_circle_glyph}

def add_glyph(name, glyph, adv, lsb):
    glyf[name] = glyph; hmtx[name] = (adv, lsb)   # glyf appends the name to the shared glyph order

for cp, (name, src) in NEW.items():
    if name in glyf: continue
    if src == "empty":
        g = Glyph(); g.numberOfContours = 0; add_glyph(name, g, 0, 0)
    elif src == "dandadouble":
        pen = TTGlyphPen(font.getGlyphSet()); gs = font.getGlyphSet(); w = hmtx["period"][0]
        gs["period"].draw(pen); gs["period"].draw(TransformPen(pen, (1, 0, 0, 1, w, 0)))
        add_glyph(name, pen.glyph(), 2 * w, hmtx["period"][1])
    elif src in DRAWN:
        g, adv = DRAWN[src](); g.recalcBounds(glyf); add_glyph(name, g, adv, g.xMin)
    else:
        add_glyph(name, copy.deepcopy(glyf[src]), *hmtx[src])
order = list(glyf.glyphOrder)
font.setGlyphOrder(order)
log(f"new glyphs: {', '.join(n for n, _ in NEW.values())}")

# ---------------------------------------------------------------- cmap
retargeted = []
for table in cmap.tables:
    if table.format not in (4, 12): continue
    for key, cp in KEY_TO_CP.items():
        if table.format == 4 and cp > 0xFFFF: continue
        old = table.cmap.get(cp)
        table.cmap[cp] = key
        if old != key and table.format == 12: retargeted.append(f"{cp:04X}->{key}")
    for cp, (name, _) in NEW.items():
        if table.format == 12 or cp <= 0xFFFF: table.cmap[cp] = name
log(f"cmap retargeted to keyboard glyphs: {len(retargeted)} ({' '.join(retargeted)})")
umap = font.getBestCmap()
def G(cp): return umap[cp]
IS, VIR, REPHA = G(0x113D0), G(0x113CE), G(0x113D1)

# ---------------------------------------------------------------- 2. read the keyboard rules
gsub = font["GSUB"].table
rules = {}   # tuple(components) -> ligature glyph
for lk in gsub.LookupList.Lookup:
    for st in lk.SubTable:
        if lk.LookupType == 7: st = st.ExtSubTable
        if getattr(st, "LookupType", lk.LookupType) != 4: continue
        for first, ligs in st.ligatures.items():
            for lig in ligs:
                rules[tuple([first] + lig.Component)] = lig.LigGlyph
log(f"keyboard ligature rules read: {len(rules)}")

# ---------------------------------------------------------------- 3. translate
CONS = set("kKgGZcCjJzqQwWNtTdDnpPbBmyrlvSxshL")
def translate(comps):
    """Keyboard components -> Unicode-input glyph sequence, or None if the rule is keyboard-only."""
    out = []
    n = len(comps)
    for i, c in enumerate(comps):
        if c == "A":
            if i == n - 2 and comps[-1] == "X": out.append(VIR); break     # 'A X' = dead form
            if i == n - 1: return None                                      # trailing A: keyboard vowel letter
            out.append(IS)
        elif c in CONS: out.append(G(0x1139A) if c == "J" else c)
        elif c in ("u", "U", "R"): out.append(c)
        elif c == "I": out.append(G(0x113BA))
        elif c == "f": out.append(REPHA)
        else: return None   # V/X/digits/keyboard vowel keys/periods
    return tuple(out)

flat, repha_rules, skipped = {}, {}, []
for comps, target in rules.items():
    t = translate(comps)
    if t is None: skipped.append((comps, target)); continue
    if t[0] in (VIR, "u", "U", "R", G(0x113BA)): skipped.append((comps, target)); continue
    if REPHA in t: repha_rules[t] = target
    else: flat[t] = target
log(f"translated: {len(flat)} flat rules, {len(repha_rules)} repha rules, {len(skipped)} keyboard-only rules skipped")

# Repha: Unicode order is REPHA + cluster; the USE moves the repha behind the base, before any
# post-base sign. So the rule becomes (base-part, REPHA) -> form, then (form, sign) -> form+sign.
abvs, blws, unresolved = {}, {}, []
flat_targets = {v: k for k, v in flat.items()}
for t, target in repha_rules.items():
    i = t.index(REPHA)
    base, signs = t[:i], t[i + 1:]
    if any(x in (IS, VIR) for x in signs) or any(x not in ("u", "U") for x in signs):
        unresolved.append((t, target)); continue
    if len(base) == 1: base_glyph = base[0]
    elif base in flat: base_glyph = flat[base]
    else: unresolved.append((t, target)); continue
    if not signs:
        abvs[(base_glyph, REPHA)] = target
    else:
        # need the form without the sign as an intermediate glyph
        inter = None
        for cand, tg in repha_rules.items():
            if cand == base + (REPHA,): inter = tg
        if inter is None: unresolved.append((t, target)); continue
        abvs[(base_glyph, REPHA)] = inter
        blws[(inter,) + signs] = target
log(f"repha: {len(abvs)} abvs rules, {len(blws)} blws rules, {len(unresolved)} unresolved")

# ---------------------------------------------------------------- 4. build GSUB lookups
def lig_lookup(mapping):
    b = LigatureSubstBuilder(font, None)
    for comps, target in mapping.items(): b.ligatures[comps] = target
    return b.build()
def single_lookup(mapping):
    b = SingleSubstBuilder(font, None); b.mapping.update(mapping); return b.build()

new_lookups = {
    "cjct": lig_lookup(flat),
    "abvs": lig_lookup(abvs),
    "blws": lig_lookup(blws),
    "psts": single_lookup({IS: VIR}),
}
ll = gsub.LookupList
feat_idx = {}
for tag, lookup in new_lookups.items():
    ll.Lookup.append(lookup); ll.LookupCount = len(ll.Lookup)
    fr = ot.FeatureRecord(); fr.FeatureTag = tag
    fr.Feature = ot.Feature(); fr.Feature.FeatureParams = None
    fr.Feature.LookupListIndex = [ll.LookupCount - 1]; fr.Feature.LookupCount = 1
    gsub.FeatureList.FeatureRecord.append(fr)
    feat_idx[tag] = len(gsub.FeatureList.FeatureRecord) - 1
gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)

def add_script(table, tag, feature_indices):
    sr = ot.ScriptRecord(); sr.ScriptTag = tag
    sr.Script = ot.Script(); sr.Script.LangSysRecord = []; sr.Script.LangSysCount = 0
    ls = ot.LangSys(); ls.LookupOrder = None; ls.ReqFeatureIndex = 0xFFFF
    ls.FeatureIndex = list(feature_indices); ls.FeatureCount = len(ls.FeatureIndex)
    sr.Script.DefaultLangSys = ls
    table.ScriptList.ScriptRecord.append(sr)
    table.ScriptList.ScriptRecord.sort(key=lambda r: r.ScriptTag)
    table.ScriptList.ScriptCount = len(table.ScriptList.ScriptRecord)

def sort_features(table):
    """FeatureList must be sorted by tag; remap every LangSys index."""
    recs = table.FeatureList.FeatureRecord
    new_order = sorted(range(len(recs)), key=lambda i: (recs[i].FeatureTag, i))
    remap = {old: new for new, old in enumerate(new_order)}
    table.FeatureList.FeatureRecord = [recs[i] for i in new_order]
    for sr in table.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is None: continue
            ls.FeatureIndex = [remap[i] for i in ls.FeatureIndex]
            if ls.ReqFeatureIndex != 0xFFFF: ls.ReqFeatureIndex = remap[ls.ReqFeatureIndex]

add_script(gsub, "tutg", [feat_idx[t] for t in ("cjct", "abvs", "blws", "psts")])
sort_features(gsub)

# ---------------------------------------------------------------- 5. GPOS: tutg shares kern
gpos = font["GPOS"].table
dflt = next(s for s in gpos.ScriptList.ScriptRecord if s.ScriptTag == "DFLT")
bases = {G(cp) for cp in KEY_TO_CP.values() if 0x11392 <= cp <= 0x113B3} | {G(0x1139A), "uni25CC"} | set(flat.values()) | set(abvs.values()) | set(blws.values())
mb = MarkBasePosBuilder(font, None)
mb.marks["u113D2"] = ("below", buildAnchor(0, 0))
for b in sorted(bases):
    g = glyf[b]
    if g.numberOfContours == 0: continue
    g.recalcBounds(glyf)
    mb.bases[b] = {"below": buildAnchor(round((g.xMin + g.xMax) / 2), 0)}
gl = gpos.LookupList; gl.Lookup.append(mb.build()); gl.LookupCount = len(gl.Lookup)
fr = ot.FeatureRecord(); fr.FeatureTag = "blwm"
fr.Feature = ot.Feature(); fr.Feature.FeatureParams = None
fr.Feature.LookupListIndex = [gl.LookupCount - 1]; fr.Feature.LookupCount = 1
gpos.FeatureList.FeatureRecord.append(fr); gpos.FeatureList.FeatureCount = len(gpos.FeatureList.FeatureRecord)
add_script(gpos, "tutg", list(dflt.Script.DefaultLangSys.FeatureIndex) + [gpos.FeatureList.FeatureCount - 1])
sort_features(gpos)
log(f"gemination mark: {len(bases)} base glyphs in blwm")

# ---------------------------------------------------------------- 6. GDEF
gdef = font["GDEF"].table
cd = gdef.GlyphClassDef.classDefs
for cp, (name, src) in NEW.items():
    cd[name] = 0 if src == "empty" else 3 if src == "gemination" else 1
for lig in set(flat.values()) | set(abvs.values()) | set(blws.values()):
    cd.setdefault(lig, 2)

# ---------------------------------------------------------------- 7. version, maxp, save
if args.version:
    v = float(args.version); font["head"].fontRevision = v
    for rec in font["name"].names:
        if rec.nameID == 5: rec.string = f"Version {v:.3f}"
        if rec.nameID == 3: rec.string = re.sub(r"Version [0-9.]+", f"Version {v:.3f}", rec.toUnicode())
    log(f"version set to {v:.3f}")
font["maxp"].numGlyphs = len(order)
font.save(args.dst)
log(f"saved {args.dst}: {len(order)} glyphs")

if args.report:
    import os; os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w") as w:
        w.write("# build_tutg report\n\n" + "\n".join(f"- {l}" for l in report) + "\n\n")
        w.write("## Keyboard-only rules skipped\n\n")
        for comps, target in skipped: w.write(f"- `{' '.join(comps)}` -> {target}\n")
        w.write("\n## Repha rules not resolved\n\n")
        for t, target in unresolved: w.write(f"- `{' '.join(t)}` -> {target}\n")
        w.write("\n## Flat rules (Unicode input -> glyph)\n\n")
        for t, target in sorted(flat.items(), key=lambda kv: kv[1]): w.write(f"- `{' '.join(t)}` -> {target}\n")
