# mallige

Tulu-Tigalari (Tulu script) font by the Tulu Baravu Font Foundry (Deepak Padukone Manjunath,
Prahlad Prasad Tantry), SIL Open Font License 1.1 (`OFL.txt`).

- `XmlAlieg(mallige)v1.4.ttf`: the font as designed, with the Latin keyboard layout.
- `XmlAlieg(mallige)v1.5.ttf`: the same font with a `tutg` OpenType layer, so Unicode
  Tulu-Tigalari text (U+11380 to U+113FF) shapes in HarfBuzz (Chrome, Firefox, Android, Linux)
  through the Universal Shaping Engine. The keyboard layout still works.
- `XmlAlieg(mallige)v1.6.ttf`: v1.5 plus the gemination mark (U+113D2), the pluta (U+113D3)
  and the dotted circle (U+25CC), drawn after the Unicode 16 code chart.

## Build

```
pip install fonttools pillow        # plus HarfBuzz (hb-shape, hb-view) for the tests
python3 tools/build_tutg.py "XmlAlieg(mallige)v1.4.ttf" "XmlAlieg(mallige)v1.5.ttf" --version 1.5 --report tests/build-report.md
python3 tools/shape_tests.py tests "XmlAlieg(mallige)v1.4.ttf" "XmlAlieg(mallige)v1.5.ttf"
python3 tools/build_tutg.py "XmlAlieg(mallige)v1.4.ttf" "XmlAlieg(mallige)v1.6.ttf" --version 1.6 --report tests/build-report.md
python3 tools/shape_tests.py tests/v1.6 "XmlAlieg(mallige)v1.6.ttf"
python3 tools/check_shapes.py "XmlAlieg(mallige)v1.6.ttf" "tests/shape-XmlAlieg(mallige)v1.5.txt"   # 25 old + 6 new cases
NODE_PATH=<node_modules with playwright> node tools/browser_shots.mjs tests/test.html tests/browser
```

`docs/tutg-notes.md` explains the keyboard layout, the glyph naming, what the build maps and
what is still open.
