# OfflineGram Composer

A locally-hosted web app for composing Instagram-style square posts. It runs a lightweight server on your machine and opens in your browser — no Electron, no native GUI framework, just a plain browser tab. Pick an image, type your text, choose a preset, preview, and export — all offline, no accounts required.

![OfflineGram Composer — wide layout](static/screenshots/ui-wide.png)

## Features

- Drag-and-drop or browse to load any image
- Enter overlay text in a single text area
- One-click preset selection (defined in `presets.json`)
- Live preview of the composited square canvas
- Export as PNG to any local folder
- Advanced zone/style controls hidden behind **Customize overlay** for power users
- 100% offline — no cloud, no login, no telemetry

## Screenshots

### Main interface

![Full interface — narrow](static/screenshots/ui-main.png)

*Left: live preview canvas. Right: source, text, preset, and export controls.*

## Quick start

**Requirements:** Python 3.11 recommended (3.9+ supported), any modern browser.

```bat
setup.bat
launch.bat
```

Then open **http://127.0.0.1:8000** in your browser.

`setup.bat` creates a virtual environment and installs all dependencies automatically. It prefers Python 3.11 for best `skia-python` compatibility.

## Workflow

1. Drop or choose an image in **Source**
2. Type your overlay text in **Text**
3. Click a preset under **Choose a style**
4. Click **Preview** to see the result
5. Click **Export PNG** to save to your chosen output folder

## Customising presets

Open `presets.json` in the project root and edit or add entries. Each preset defines one or more *zones* — text blocks, bands, or shapes — with full control over font, size, color, opacity, position, shadow, and outline.

Restart the app after saving changes; the preset list reloads on the next page load.

## Advanced overlay controls

Click **Customize overlay** in the control panel to expose per-zone settings without editing JSON — useful for one-off tweaks before export.

## Stack

| Layer | Library |
|---|---|
| Backend | FastAPI + Uvicorn |
| Image rendering | skia-python |
| Image loading | Pillow |
| Frontend | Vanilla HTML / CSS / JS |
| Tests | pytest + FastAPI TestClient |

## Running tests

```powershell
venv\Scripts\python -m pytest -v
```

## Project structure

```
app.py            FastAPI application and route handlers
processor.py      Skia rendering engine and file utilities
presets.py        Preset loading and zone resolution
presets.json      Editable preset definitions
setup.bat         One-time environment setup
launch.bat        Start the local server
templates/        HTML template
static/           CSS, JS, screenshots
fonts/            Bundled font files
tests/            pytest test suite
```

## Roadmap

### Batch mode — folder import & quote file

Point the app at a folder of images and a plain text file of quotes (one per line). The app processes every image in the folder, stamps each one with the next quote from the file using the active preset, and writes all exported PNGs to the same output folder in one operation. No manual clicking per image.

### Batch mode — multi-zone text files

Import a structured text file where each entry contains separate fields for multiple text zones on one image (e.g. a title line, a subtitle line, a caption). The app maps each field to its corresponding zone on the canvas, composites all images in the batch, and exports them together. Useful for recurring content formats where every post has the same layout but different copy in each zone.

---

## License

MIT — see [LICENSE](LICENSE).
