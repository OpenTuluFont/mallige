# Tulu-Tigalari (`tutg`) layer for mallige: notes and glyph map

Sandeep Kalpane, September 2026. Companion to `tools/build_tutg.py`. Everything below was
read from `XmlAlieg(mallige)v1.4.ttf` with fontTools 4.62 and tested with HarfBuzz 14.2.1.

## 1. What v1.4 contains

- 1791 glyphs, unitsPerEm 1000, made in FontLab (2022), designer Prahlad Prasad Tantry (name id 9).
- The working layout is a **Latin keyboard hack**: the ASCII code points map to Tulu glyphs
  (`k` = KA, `t` = TA ...), one `liga` lookup with 1527 rules under `DFLT`/`latn` builds
  conjuncts, and one `kern` lookup (1309 pairs and a class matrix) pulls subjoined forms,
  vowel signs, the virama and the repha back under or over the base. Stacking is therefore
  done by kerning: a subjoined glyph sits after the base with a negative kern equal to the
  base's advance.
- The 80 Unicode Tulu-Tigalari code points map to glyphs named `uXXXXX`, but nothing in
  GSUB/GPOS references them, so Unicode text shaped as isolated glyphs (no reordering, no
  conjuncts, signs floating after the base).
- **Missing** assigned code points: 113D0 CONJOINER, 113D1 REPHA, 113D2 GEMINATION MARK,
  113D3 PLUTA, 113D4 DANDA, 113D5 DOUBLE DANDA, 113E1 VEDIC TONE SVARITA, 113E2 VEDIC TONE ANUDATTA.
- **Unassigned** code points mapped: 1138A, 1138C, 1138D, 1138F (letters) and 113C1, 113C3,
  113C4, 113C6 (signs). These carry the short e / o forms of the Academy chart, which Unicode
  16 to 18 do not encode. Left as they are (see section 5).

## 2. Keyboard key to Unicode (verified by outline identity, `tools/match_hack.py`)

| keys | characters |
|---|---|
| k K g G Z | KA KHA GA GHA NGA |
| c C j (J alt) z | CA CHA JA JHA NYA |
| q Q w W N | TTA TTHA DDA DDHA NNA |
| t T d D n | TA THA DA DHA NA |
| p P b B m | PA PHA BA BHA MA |
| y r l v | YA RA LA VA |
| S x s h L | SHA SSA SA HA LLA |
| a u U R | vowel signs AA, U, UU, vocalic R |
| E e o O Y i I | sign EE, short-e sign (113C1), short-o sign (113C3), AI-like (113C4), AU length mark, sign I hook, sign II hook |
| M H F A | anusvara, visarga, candra anunasika, virama |
| f | repha tick |
| X | dead-consonant marker (empty): `k A X` = KA with the virama attached |
| V | variant prefix (empty): numerals 10/100/1000, `za zu zuu zza sza fa`, `xxrhaxx` (RRA), `xxzhaxx` (LLLA) |
| 0-9 . | Tulu numerals; `.` is a full-height bar (the danda) |

Same drawing, different advance (keyboard vs Unicode glyph): KHA 871/808, DA 418/391,
sign U 346/486, sign UU 444/597, sign AA 253/295, candra anunasika 355/413. The kern table was
built for the keyboard glyphs, so the build points the code points at those.

## 3. Ligature naming

- `k_A_t` = KA + conjoiner + TA as one glyph, base included. Many are linear ligatures (`k_A_k`
  is two KA side by side, as in Malayalam), some stack (`k_A_r`).
- Rules that **start with** `A` give the subjoined forms placed after a base: `A_k` (one
  consonant), `k_A_t.under` (a stack). They are lowered glyphs, kerned back under the base.
- `k_A_X` = KA with the virama attached (dead consonant). `k_u`, `k_U` = precomposed U / UU
  forms, present for 13 consonants (k g C j q N t d n B r S h); the others take the spacing
  sign, kerned. `y_f` = YA with the repha tick; `y_f_u`, `m_A_m_f` ... likewise.
- `S_A_r_I` = śrī. `A_A`, `A_a`, `A_i`, `E_A`, `O_A` ... are keyboard ways to type independent
  vowels and are not needed for Unicode input.

## 4. What the build does

1. cmap: 43 Tulu-Tigalari code points now point at the keyboard glyph (table above), the
   conjoiner gets a new empty glyph `u113D0`, the danda is the full stop, the double danda a new
   glyph `u113D5` made of two of them. The `uXXXXX` duplicates stay in the font, unreferenced.
2. GSUB script `tutg` (default language system):
   - `cjct`: the 1461 keyboard rules that make sense for Unicode input, translated
     (`A` -> CONJOINER, trailing `A X` -> VIRAMA, `f` -> REPHA, `I` -> sign II), one lookup,
     longest match, so the same glyph comes out that the keyboard produces.
   - `abvs`: the 8 repha forms, matched after the USE has moved the repha behind the base.
   - `blws`: repha form + sign U/UU (8 rules).
   - `psts`: a conjoiner that no rule consumed becomes the visible virama, so a missing
     conjunct never renders as two plain consonants.
   - 49 keyboard-only rules are skipped (listed in the build report).
3. GPOS script `tutg` shares the existing `kern` feature.
4. GDEF: the new glyphs get a class; ligature targets are class 2.
5. Version: name ids 3 and 5 and `head.fontRevision` set to 1.500.

Semantics follow Unicode: CONJOINER (Invisible_Stacker) forms conjuncts, VIRAMA (Pure_Killer)
is a visible sign: KA + VIRAMA gives `k_A_X`, KA + VIRAMA + TA gives `k_A_X` + TA.

## 5. Not done, and why

- **Vedic tones (113E1, 113E2)**: need drawing. (113D2 gemination mark, 113D3 pluta and the
  dotted circle U+25CC are in v1.6: `tools/build_tutg.py`, drawn after the Unicode 16 chart; the
  mark attaches below the base through `blwm`, and the USE order is consonant, mark, vowel sign.)
  The Unicode chart shows a small mark below, a "2"-like curl, a short slanted stroke above
  and a small hook below. Any of these can be added to the build as soon as a glyph exists.
- **Vowel signs stay spacing glyphs** (no GDEF mark class, no anchors). The design handles
  them by precomposed forms and kerning, and that renders correctly, so anchors are not
  needed for this font. Marking them as GDEF marks would make HarfBuzz zero their advance
  and break the kerning approach.
- **Repha over sign II** (`f_I`) has no Unicode equivalent I could derive; skipped.
- **Short e / o** on unassigned code points: the USE does not treat them as vowel signs, so
  a pre-base short-e sign is not moved before the consonant. A font can only work around it
  with a reordering trick (ligate, then split); the real fix is a Unicode proposal.
- **Three-consonant stacks** come out as the keyboard produces them (`N_A_k` + `A_t` for
  NNA + KA + TA), because the rule set has no three-consonant ligature for that case.
- ASCII digits still render as Tulu numerals (keyboard behaviour, unchanged).

## 6. Questions for the maintainers

1. Keyboard or Unicode advance for KHA, DA, sign U, sign UU, sign AA, candra anunasika?
2. JHA: `J` (narrow) or `J.1` (wide, currently at 1139A)?
3. Is the 3-consonant stack rendering (section 5) what you intend?
4. File name and version: `XmlAlieg(mallige)v1.5.ttf`, version 1.500?
5. Do the Glyphs/FontLab sources exist? The 4 missing marks are easier to draw there.

## 7. Evidence

- `tools/shape_tests.py`: 25 cases through hb-shape and hb-view; `tests/shape-*.txt` hold the
  glyph streams before and after, `tests/sheet.png` the side-by-side rendering.
- `tests/browser/*.png`: the same page in Chromium, Firefox and WebKit (Playwright); WebKit on
  macOS shapes with CoreText, so that is the Safari result.
