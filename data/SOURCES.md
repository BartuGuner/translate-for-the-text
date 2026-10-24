# LexiHover Data Sources & Licensing

LexiHover relies exclusively on open dictionary and linguistic data. The runtime runs 100% offline using `data/dictionary.db` which is compiled ahead of time by `tools/build_dictionary.py`.

---

## 1. English Wiktionary (via Kaikki.org / wiktextract)

- **Source**: [kaikki.org English Wiktionary data](https://kaikki.org/dictionary/English/)
- **Extractor**: `wiktextract` by Tatu Ylonen
- **Content used**: English headwords with Turkish (`tr`) translations, parts of speech, and irregular inflected forms (`forms`).
- **License**: **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** and GNU Free Documentation License (GFDL).
- **Attribution**: Derived from Wiktionary (English edition) entries maintained by the Wikimedia community and parsed by wiktextract.

---

## 2. FreeDict English-Turkish Dictionary (`eng-tur`)

- **Source**: [FreeDict eng-tur dictionary 0.3](https://freedict.org/)
- **Maintainers**: FreeDict project contributors
- **Content used**: Additional English-to-Turkish translation glosses for words not covered in the Wiktionary extract.
- **License**: **GNU General Public License v2.0 or later (GPL-2.0-or-later)**.
- **Attribution**: Derived from FreeDict `eng-tur` 0.3 TEI XML source.

---

## 3. Simplemma (Lemmatizer)

- **Source**: [Simplemma Python package](https://github.com/adbar/simplemma) by Adrien Barbaresi
- **Content used**: Pure Python offline lemmatization data and algorithms for English inflections.
- **License**: **MIT License**.
