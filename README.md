# LexiHover

**Offline English-to-Turkish Reading Assistant**

LexiHover is a lightweight, local web application designed for reading English texts with instantaneous word-level English-to-Turkish translations on hover. It runs 100% locally and offline without external network calls, ML models, or internet access at runtime.

---

## Features

- **Ahead-of-Time Word Translation**: Translates all unique words across the text upfront using a prebuilt offline SQLite dictionary.
- **Reading View & Hover Tooltips**: Clean typography preserving original formatting, paragraphs, and whitespace. Hover over any word to see its Turkish meanings, part of speech, and lemma.
- **Pin & Save Favorites**: Click to pin the tooltip bubble. Press the star (☆) button to save words into your personal persistent list.
- **Favorites Management**: Instant search, date added, context sentence snippet, delete confirmation, and UTF-8 BOM CSV export compatible with Microsoft Excel.
- **Customizable Reader Settings**: 4 font sizes, light/dark themes, and optional dotted underline for unknown words.
- **Privacy & Security**: Binds exclusively to `127.0.0.1`. Never sends text over the internet.
- **Portability**: Packaged for offline deployment on other computers (Windows 10/11, macOS, Linux) with ready-to-run startup scripts and bundled wheelhouse.

---

## Dictionary Statistics

Built using `tools/build_dictionary.py` merging English Wiktionary (via Kaikki.org) and FreeDict:

- **Headword entries**: 32,139
- **Distinct English headwords**: 31,217
- **Turkish meanings**: 88,478
- **Irregular inflected forms**: 6,053 (plus dynamic lemmatization via Simplemma)
- **Quality Gate**: 40/40 (100%) common test words verified with Turkish meanings
- **Database Size**: 5.8 MB SQLite (`data/dictionary.db`)

---

## Quick Start (One-Command)

### On Windows 10/11
Double-click `start.bat` (or run in Command Prompt / PowerShell):
```cmd
start.bat
```

### On macOS / Linux
Open a terminal in the project folder and run:
```bash
./start.sh
```

Both scripts will automatically:
1. Detect Python (3.10+ or 3.9+).
2. Create a local virtual environment (`.venv`) if not present.
3. Install dependencies from the bundled `wheelhouse/` folder **completely offline** (`--no-index`).
4. Start the server on `http://127.0.0.1:5057` and open your default browser.

---

## Manual Installation & Testing

If you prefer to run manually:

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# 2. Install dependencies offline from wheelhouse
pip install --no-index --find-links wheelhouse -r requirements.txt

# 3. Run automated tests (pytest)
pytest

# 4. Start LexiHover
python -m app.main
```

Then visit: [http://127.0.0.1:5057/](http://127.0.0.1:5057/)

---

## Configuration

Override configuration via environment variables:

- `LEXIHOVER_PORT`: Port number (default: `5057`).
- `LEXIHOVER_USERDATA`: Path to user database directory (default: `./userdata`).

---

## Rebuilding the Dictionary

The dictionary is shipped prebuilt in `data/dictionary.db`. If you ever need to recompile it from raw sources on a connected computer:

```bash
# Automatically download raw sources into build_cache/ and compile:
python tools/build_dictionary.py --download

# Or compile from existing local source files:
python tools/build_dictionary.py --kaikki build_cache/kaikki-en.jsonl --freedict build_cache/eng-tur/eng-tur.tei
```

---

## Backing Up Favorites

All your saved favorites are stored in a single SQLite database file:
```
userdata/user.db
```
To back up or transfer your saved words to another computer, simply copy the `userdata/` folder. You can also export your list anytime from the Favorites tab as a CSV file.

---

## Troubleshooting

- **Python not found**:
  - Windows: Install Python from [python.org](https://www.python.org/) and make sure to check **"Add python.exe to PATH"** during installation.
  - macOS/Linux: Install Python via Homebrew (`brew install python`) or your distribution's package manager (`sudo apt install python3 python3-venv`).
- **Port 5057 in use**:
  Set another port before running:
  - Windows: `set LEXIHOVER_PORT=5058 && start.bat`
  - macOS/Linux: `LEXIHOVER_PORT=5058 ./start.sh`
- **Missing wheels when moving to another OS**:
  The `wheelhouse/` directory contains pre-downloaded wheels for Windows (CPython 3.10 through 3.14 x64), macOS (Apple Silicon arm64 & Intel x86_64), and Linux x86_64. If deploying to an uncommon architecture, run:
  ```bash
  pip download -r requirements.txt -d wheelhouse --platform <target_platform> --only-binary=:all:
  ```

---

## Architecture & Design Decisions

1. **Context-Free Word Translation**:
   Sentence-level ML models require substantial runtime resources and dependencies. LexiHover focuses on fast, distraction-free reading by translating individual words context-free and displaying multiple prioritized Turkish senses.
2. **5-Stage Lookup Cascade**:
   Lookup prioritizes exact lowercase word, irregular form mapping (e.g. *went* -> *go*, *children* -> *child*), Simplemma lemmatization (e.g. *running* -> *run*, *books* -> *book*), possessive stripping (*'s*, *s'*), and hyphen segmentation.
3. **Chunked Rendering for Large Documents**:
   Documents up to 50,000 characters (approx. 10,000 words) are supported. For texts over 5,000 words, LexiHover chunks DOM creation per paragraph using `requestAnimationFrame` to keep the UI smooth and responsive.
4. **Single-Listener Event Delegation**:
   A single event listener on the reading container handles hover, pin, and focus interactions across thousands of word tokens without memory overhead.
5. **Zero External Frontend Dependencies**:
   Clean modern UI built with vanilla CSS, custom SVG icons, and system font stacks for instant loading and zero runtime CDN requirements.
