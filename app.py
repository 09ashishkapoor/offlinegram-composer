from __future__ import annotations

import json
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from presets import (
    PresetConfigError,
    build_batch_quote_zones,
    build_batch_structured_zones,
    build_preset_zones,
    load_preset_catalog,
    resolve_batch_preset_mode,
)
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
    parse_structured_text_lines,
    parse_text_entries,
    pick_native_path,
    save_png,
    NATIVE_PICKER_MODES,
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


def _parse_single_image_structured_text_values(text: str) -> dict[str, str]:
    stripped = text.strip()
    if not stripped:
        return {
            "number": "",
            "name": "",
            "title": "",
            "subtitle": "",
            "caption": "",
        }

    try:
        return parse_structured_text_lines(stripped)[0]
    except ProcessorError:
        pass

    parts = [line.strip() for line in stripped.splitlines() if line.strip()]
    return {
        "number": parts[0] if len(parts) >= 1 else "",
        "name": parts[1] if len(parts) >= 2 else "",
        "title": parts[0] if len(parts) >= 1 else "",
        "subtitle": parts[1] if len(parts) >= 2 else "",
        "caption": " ".join(parts[2:]) if len(parts) >= 3 else "",
    }


def _resolve_single_image_render_context(
    preset_id: str | None,
    text: str,
    overlay_json: str | None,
) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    overlay = _parse_overlay_json(overlay_json)
    if overlay is not None:
        if preset_id:
            try:
                if resolve_batch_preset_mode(preset_id) == "structured":
                    return overlay, _parse_single_image_structured_text_values(text)
            except PresetConfigError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return overlay, None
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")
    try:
        if resolve_batch_preset_mode(preset_id) == "structured":
            return build_batch_structured_zones(preset_id), _parse_single_image_structured_text_values(text)
        return build_preset_zones(preset_id, text), None
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


async def _read_text_content(text_file: UploadFile | None, text_path: str | None) -> str:
    if text_file and text_file.filename:
        raw = await text_file.read()
    elif text_path:
        try:
            source = Path(text_path).expanduser().resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail="Selected text file was not found.") from exc
        if not source.is_file():
            raise HTTPException(status_code=400, detail="Selected text path is not a file.")
        try:
            raw = source.read_bytes()
        except OSError as exc:
            raise HTTPException(status_code=400, detail="Unable to read selected text file.") from exc
    else:
        raise HTTPException(status_code=400, detail="Upload a text file or choose one from disk.")

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Text file must be UTF-8 encoded.") from exc


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


def _paired_preset_batch_inputs(
    image_dir: str,
    text_content: str,
    preset_id: str,
) -> tuple[list[Path], list[Any], str]:
    try:
        images = list_images(image_dir)
        batch_mode = resolve_batch_preset_mode(preset_id)
        entries: list[Any]
        if batch_mode == "structured":
            entries = parse_structured_text_lines(text_content)
        else:
            entries = parse_quote_lines(text_content)
    except (PresetConfigError, ProcessorError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not images:
        raise HTTPException(status_code=400, detail="No supported images were found in the selected folder.")
    if len(images) != len(entries):
        if batch_mode == "structured":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Batch image count and structured-entry count must match exactly. "
                    f"Found {len(images)} images and {len(entries)} structured entries."
                ),
            )
        raise HTTPException(
            status_code=400,
            detail="Process stopped because quotes or images ran out.",
        )
    return images, entries, batch_mode


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


@app.post("/api/pick")
async def pick_path(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get("mode") or "").strip()
    if mode not in NATIVE_PICKER_MODES:
        raise HTTPException(status_code=400, detail="Invalid picker mode.")

    initial_path_raw = payload.get("initial_path")
    initial_path = initial_path_raw.strip() if isinstance(initial_path_raw, str) else None
    try:
        selected_path = pick_native_path(mode=mode, initial_path=initial_path)
    except ProcessorError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return {"path": selected_path, "cancelled": selected_path is None}


@app.post("/api/preview")
async def preview_single(
    image: UploadFile | None = File(default=None),
    image_path: str | None = Form(default=None),
    preset_id: str | None = Form(default=None),
    text: str = Form(default=""),
    overlay_json: str | None = Form(default=None),
) -> dict[str, str]:
    zones, text_values = _resolve_single_image_render_context(preset_id, text, overlay_json)
    base_image = await _load_single_image(image, image_path)
    png_data = processor.render_image(base_image, name="", meaning="", zones=zones, text_values=text_values)
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
    zones, text_values = _resolve_single_image_render_context(preset_id, text, overlay_json)
    base_image = await _load_single_image(image, image_path)
    png_data = processor.render_image(base_image, name="", meaning="", zones=zones, text_values=text_values)
    saved_path = save_png(_validate_output_dir(output_dir), png_data)
    return {"saved_to": str(saved_path), "filename": saved_path.name}


@app.post("/api/batch/preview")
async def preview_batch(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    zones = _parse_zones_json(zones_json)
    text_content = await _read_text_content(text_file, text_path)
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
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    output_dir: str = Form(default=""),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    zones = _parse_zones_json(zones_json)
    text_content = await _read_text_content(text_file, text_path)
    images, entries = _paired_batch_inputs(image_dir, text_content)
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    for image_path, entry in zip(images, entries):
        png_data = processor.render_from_path(image_path, entry["name"], entry["meaning"], zones)
        files.append(str(save_png(output_root, png_data)))
    return {"saved_count": len(files), "files": files}


@app.post("/api/batch/quotes/preview")
async def preview_batch_quotes(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")

    text_content = await _read_text_content(text_file, text_path)
    images, entries, batch_mode = _paired_preset_batch_inputs(image_dir, text_content, preset_id)
    previews: list[dict[str, str]] = []
    for image_path, entry in list(zip(images, entries))[: max(1, min(sample_count, 5))]:
        try:
            if batch_mode == "structured":
                zones = build_batch_structured_zones(preset_id)
                png_data = processor.render_from_path(
                    image_path,
                    name="",
                    meaning="",
                    zones=zones,
                    text_values=entry,
                )
                previews.append(
                    {
                        "filename": image_path.name,
                        "number": entry["number"],
                        "name": entry["name"],
                        "title": entry["title"],
                        "subtitle": entry["subtitle"],
                        "caption": entry["caption"],
                        "image_b64": image_file_to_base64(png_data),
                    }
                )
            else:
                zones = build_batch_quote_zones(preset_id, entry)
                png_data = processor.render_from_path(image_path, name="", meaning="", zones=zones)
                previews.append(
                    {
                        "filename": image_path.name,
                        "quote": entry,
                        "image_b64": image_file_to_base64(png_data),
                    }
                )
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"previews": previews, "mode": batch_mode}


@app.post("/api/batch/quotes/generate")
async def generate_batch_quotes(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    output_dir: str = Form(default=""),
) -> dict[str, Any]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    if not preset_id:
        raise HTTPException(status_code=400, detail="Choose a preset.")

    text_content = await _read_text_content(text_file, text_path)
    images, entries, batch_mode = _paired_preset_batch_inputs(image_dir, text_content, preset_id)
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    for image_path, entry in zip(images, entries):
        try:
            if batch_mode == "structured":
                zones = build_batch_structured_zones(preset_id)
                png_data = processor.render_from_path(
                    image_path,
                    name="",
                    meaning="",
                    zones=zones,
                    text_values=entry,
                )
            else:
                zones = build_batch_quote_zones(preset_id, entry)
                png_data = processor.render_from_path(image_path, name="", meaning="", zones=zones)
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        files.append(str(save_png(output_root, png_data)))
    return {"saved_count": len(files), "files": files, "mode": batch_mode}
