from __future__ import annotations

import json
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from presets import PresetConfigError, build_batch_quote_zones, build_preset_zones, load_preset_catalog
from processor import (
    BASE_DIR,
    DEFAULT_ZONES,
    FONTS_DIR,
    ProcessorError,
    SkiaProcessor,
    browse_directory,
    cleanup_temp_files,
    ensure_runtime_dirs,
    image_file_to_base64,
    list_font_choices,
    list_images,
    normalize_zones,
    parse_quote_lines,
    parse_text_entries,
    save_png,
)


processor = SkiaProcessor(FONTS_DIR)
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_dirs()
    cleanup_temp_files()
    yield


app = FastAPI(title="OfflineGram Composer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/fonts", StaticFiles(directory=FONTS_DIR), name="fonts")


def _parse_zones_json(zones_json: str | None) -> list[dict[str, Any]]:
    if not zones_json:
        return normalize_zones(DEFAULT_ZONES)
    try:
        payload = json.loads(zones_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid zones JSON.") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="Zones payload must be a list.")
    return normalize_zones(payload)


def _parse_overlay_json(overlay_json: str | None) -> list[dict[str, Any]] | None:
    if not overlay_json:
        return None
    try:
        payload = json.loads(overlay_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid overlay JSON.") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="Overlay payload must be a list.")
    return payload


def _resolve_single_image_zones(
    preset_id: str | None,
    text: str,
    overlay_json: str | None,
) -> list[dict[str, Any]]:
    overlay = _parse_overlay_json(overlay_json)
    if overlay is not None:
        return overlay
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")
    try:
        return build_preset_zones(preset_id, text)
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _load_single_image(upload: UploadFile | None, image_path: str | None) -> Image.Image:
    try:
        if upload and upload.filename:
            data = await upload.read()
            return Image.open(BytesIO(data))
        if image_path:
            return Image.open(image_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Selected image was not found.") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail="Unable to read image input.") from exc

    raise HTTPException(status_code=400, detail="Provide an uploaded image or an image path.")


def _validate_output_dir(output_dir: str | None) -> str:
    if not output_dir:
        raise HTTPException(status_code=400, detail="Select an output folder.")
    return output_dir


def _paired_batch_inputs(image_dir: str, text_content: str) -> tuple[list[Path], list[dict[str, str]]]:
    try:
        images = list_images(image_dir)
        entries = parse_text_entries(text_content)
    except ProcessorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not images:
        raise HTTPException(status_code=400, detail="No supported images were found in the selected folder.")
    if len(images) != len(entries):
        raise HTTPException(
            status_code=400,
            detail=(
                "Batch image count and text-entry count must match exactly. "
                f"Found {len(images)} images and {len(entries)} text entries."
            ),
        )
    return images, entries


def _paired_quote_batch_inputs(image_dir: str, text_content: str) -> tuple[list[Path], list[str]]:
    try:
        images = list_images(image_dir)
        quotes = parse_quote_lines(text_content)
    except ProcessorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not images:
        raise HTTPException(status_code=400, detail="No supported images were found in the selected folder.")
    if len(images) != len(quotes):
        raise HTTPException(
            status_code=400,
            detail="Process stopped because quotes or images ran out.",
        )
    return images, quotes


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.get("/api/fonts")
async def get_fonts() -> dict[str, Any]:
    return {"fonts": list_font_choices(FONTS_DIR)}


@app.get("/api/defaults")
async def get_defaults() -> dict[str, Any]:
    return {"zones": DEFAULT_ZONES}


@app.get("/api/presets")
async def get_presets() -> dict[str, Any]:
    try:
        return {
            "presets": load_preset_catalog(),
            "helper_text": "Edit presets in presets.json (in this project root, next to app.py).",
        }
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/browse")
async def browse(path: str | None = None) -> dict[str, Any]:
    try:
        return browse_directory(path)
    except ProcessorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/preview")
async def preview_single(
    image: UploadFile | None = File(default=None),
    image_path: str | None = Form(default=None),
    preset_id: str | None = Form(default=None),
    text: str = Form(default=""),
    overlay_json: str | None = Form(default=None),
) -> dict[str, str]:
    zones = _resolve_single_image_zones(preset_id, text, overlay_json)
    base_image = await _load_single_image(image, image_path)
    png_data = processor.render_image(base_image, name="", meaning="", zones=zones)
    return {"image_b64": image_file_to_base64(png_data)}


@app.post("/api/generate")
async def generate_single(
    image: UploadFile | None = File(default=None),
    image_path: str | None = Form(default=None),
    preset_id: str | None = Form(default=None),
    text: str = Form(default=""),
    overlay_json: str | None = Form(default=None),
    output_dir: str = Form(default=""),
) -> dict[str, Any]:
    zones = _resolve_single_image_zones(preset_id, text, overlay_json)
    base_image = await _load_single_image(image, image_path)
    png_data = processor.render_image(base_image, name="", meaning="", zones=zones)
    saved_path = save_png(_validate_output_dir(output_dir), png_data)
    return {"saved_to": str(saved_path), "filename": saved_path.name}


@app.post("/api/batch/preview")
async def preview_batch(
    text_file: UploadFile = File(...),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    zones = _parse_zones_json(zones_json)
    text_content = (await text_file.read()).decode("utf-8")
    images, entries = _paired_batch_inputs(image_dir, text_content)
    previews: list[dict[str, str]] = []
    for image_path, entry in list(zip(images, entries))[: max(1, min(sample_count, 5))]:
        png_data = processor.render_from_path(image_path, entry["name"], entry["meaning"], zones)
        previews.append(
            {
                "filename": image_path.name,
                "name": entry["name"],
                "meaning": entry["meaning"],
                "image_b64": image_file_to_base64(png_data),
            }
        )
    return {"previews": previews}


@app.post("/api/batch/generate")
async def generate_batch(
    text_file: UploadFile = File(...),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    output_dir: str = Form(default=""),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    zones = _parse_zones_json(zones_json)
    text_content = (await text_file.read()).decode("utf-8")
    images, entries = _paired_batch_inputs(image_dir, text_content)
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    for image_path, entry in zip(images, entries):
        png_data = processor.render_from_path(image_path, entry["name"], entry["meaning"], zones)
        files.append(str(save_png(output_root, png_data)))
    return {"saved_count": len(files), "files": files}


@app.post("/api/batch/quotes/preview")
async def preview_batch_quotes(
    text_file: UploadFile = File(...),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")

    text_content = (await text_file.read()).decode("utf-8")
    images, quotes = _paired_quote_batch_inputs(image_dir, text_content)
    previews: list[dict[str, str]] = []
    for image_path, quote in list(zip(images, quotes))[: max(1, min(sample_count, 5))]:
        try:
            zones = build_batch_quote_zones(preset_id, quote)
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        png_data = processor.render_from_path(image_path, name="", meaning="", zones=zones)
        previews.append(
            {
                "filename": image_path.name,
                "quote": quote,
                "image_b64": image_file_to_base64(png_data),
            }
        )
    return {"previews": previews}


@app.post("/api/batch/quotes/generate")
async def generate_batch_quotes(
    text_file: UploadFile = File(...),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    output_dir: str = Form(default=""),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")

    text_content = (await text_file.read()).decode("utf-8")
    images, quotes = _paired_quote_batch_inputs(image_dir, text_content)
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    for image_path, quote in zip(images, quotes):
        try:
            zones = build_batch_quote_zones(preset_id, quote)
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        png_data = processor.render_from_path(image_path, name="", meaning="", zones=zones)
        files.append(str(save_png(output_root, png_data)))
    return {"saved_count": len(files), "files": files}
