# mallige

Tulu-Tigalari (Tulu script) font by the Tulu Baravu Font Foundry (Deepak Padukone Manjunath,
Prahlad Prasad Tantry), SIL Open Font License 1.1 (`OFL.txt`).

- `XmlAlieg(mallige)v1.4.ttf`: the font as designed, with the Latin keyboard layout.
- `XmlAlieg(mallige)v1.5.ttf`: the same font with a `tutg` OpenType layer, so Unicode
  Tulu-Tigalari text (U+11380 to U+113FF) shapes in HarfBuzz (Chrome, Firefox, Android, Linux)
  through the Universal Shaping Engine. The keyboard layout still works.

## Build

```
pip install fonttools pillow        # plus HarfBuzz (hb-shape, hb-view) for the tests
python3 tools/build_tutg.py "XmlAlieg(mallige)v1.4.ttf" "XmlAlieg(mallige)v1.5.ttf" --version 1.5 --report tests/build-report.md
python3 tools/shape_tests.py tests "XmlAlieg(mallige)v1.4.ttf" "XmlAlieg(mallige)v1.5.ttf"
NODE_PATH=<node_modules with playwright> node tools/browser_shots.mjs tests/test.html tests/browser
```

`docs/tutg-notes.md` explains the keyboard layout, the glyph naming, what the build maps and
what is still open.
