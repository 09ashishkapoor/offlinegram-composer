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
    structured_fields_for_preset,
    create_preset,
    delete_preset,
    PRESETS_CONFIG_PATH,
    update_preset,
    resolve_batch_preset_mode,
    validate_zone_list,
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
    normalize_export_format,
    save_rendered_image,
    image_file_to_base64,
    list_font_choices,
    list_images,
    normalize_zones,
    parse_quote_lines,
    parse_structured_delimited_text_lines,
    parse_field_mapping_json,
    detect_structured_import_format,
    extract_delimited_headers,
    suggest_structured_field_mapping,
    parse_structured_text_lines,
    parse_text_entries,
    pick_native_path,
    validate_export_quality,
    validate_filename_template,
    NATIVE_PICKER_MODES,
)


processor = SkiaProcessor(FONTS_DIR)
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _preset_collection_payload() -> dict[str, Any]:
    return {
        "presets": load_preset_catalog(config_path=PRESETS_CONFIG_PATH),
        "helper_text": "Presets are editable in-app and saved to presets.json in this project folder.",
    }


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
    try:
        return validate_zone_list(payload, preset_id="overlay")
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    except ProcessorError as exc:
        strict_error = exc

    parts = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(parts) < 3:
        raise ProcessorError(
            "Structured presets require either one line in the form 1. Name: Caption or three non-empty lines for number, name, and caption."
        ) from strict_error

    return {
        "number": parts[0] if len(parts) >= 1 else "",
        "name": parts[1] if len(parts) >= 2 else "",
        "title": parts[0] if len(parts) >= 1 else "",
        "subtitle": parts[1] if len(parts) >= 2 else "",
        "caption": " ".join(parts[2:]) if len(parts) >= 3 else "",
    }


def _parse_export_options(
    format_value: str | None,
    quality_value: str | int | None,
    filename_template: str | None,
) -> dict[str, Any]:
    try:
        export_format = normalize_export_format(format_value)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Supported formats are PNG, JPG, and WebP.",
        ) from exc

    if quality_value is None:
        quality: int | None = None
    elif isinstance(quality_value, int):
        quality = quality_value
    else:
        quality_text = str(quality_value).strip()
        if not quality_text:
            quality = None
        else:
            try:
                quality = int(quality_text)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Quality must be an integer between 1 and 100.",
                ) from exc

    try:
        quality = validate_export_quality(export_format, quality)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        safe_template = validate_filename_template(filename_template)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "format": export_format,
        "quality": quality,
        "template": safe_template,
    }


def _resolve_export_filename_context(
    *,
    index: int,
    source: Path | str,
    text_values: dict[str, str] | str | None = None,
    fallback_text: str | None = None,
    preset_id: str | None = None,
) -> dict[str, str]:
    source_name = Path(source).stem if source else "image"
    name_value = ""
    if isinstance(text_values, dict):
        name_value = (
            text_values.get("name", "")
            or text_values.get("meaning", "")
            or text_values.get("title", "")
            or text_values.get("subtitle", "")
            or text_values.get("caption", "")
            or text_values.get("number", "")
        )
    elif isinstance(text_values, str):
        name_value = text_values
    if not name_value and fallback_text:
        name_value = fallback_text

    return {
        "index": str(index),
        "source": source_name,
        "name": name_value,
        "preset": preset_id or "",
    }


def _single_image_preset_uses_structured_fields(preset_id: str) -> bool:
    try:
        preset = next(preset for preset in load_preset_catalog(config_path=PRESETS_CONFIG_PATH) if preset["id"] == preset_id)
    except StopIteration as exc:
        raise PresetConfigError(f"Unknown preset '{preset_id}'.") from exc

    return any(
        zone.get("type") == "text" and zone.get("text_source") in {"number", "name", "caption", "title", "subtitle"}
        for zone in preset["zones"]
    )


def _resolve_single_image_render_context(
    preset_id: str | None,
    text: str,
    overlay_json: str | None,
) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    overlay = _parse_overlay_json(overlay_json)
    if overlay is not None:
        if preset_id:
            try:
                if _single_image_preset_uses_structured_fields(preset_id):
                    return overlay, _parse_single_image_structured_text_values(text)
            except (PresetConfigError, ProcessorError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return overlay, None
    if not preset_id:
        raise HTTPException(
            status_code=400,
            detail="Choose a preset when using single-image generation without an overlay override.",
        )
    try:
        if _single_image_preset_uses_structured_fields(preset_id):
            return build_batch_structured_zones(preset_id, config_path=PRESETS_CONFIG_PATH), _parse_single_image_structured_text_values(text)
        return build_preset_zones(preset_id, text, config_path=PRESETS_CONFIG_PATH), None
    except (PresetConfigError, ProcessorError) as exc:
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


def _paired_preset_batch_inputs(
    image_dir: str,
    text_content: str,
    preset_id: str,
    import_format: str | None = None,
    field_mapping_json: str | None = None,
) -> tuple[list[Path], list[Any], str]:
    try:
        images = list_images(image_dir)
        batch_mode = resolve_batch_preset_mode(preset_id, config_path=PRESETS_CONFIG_PATH)
        entries: list[Any]
        if batch_mode == "structured":
            selected_format = detect_structured_import_format(text_content, import_format=import_format)
            if selected_format in {"csv", "tsv"}:
                parsed_mapping = parse_field_mapping_json(field_mapping_json)
                preset_fields = structured_fields_for_preset(preset_id, config_path=PRESETS_CONFIG_PATH)
                required_fields = tuple(preset_fields)
                entries, _ = parse_structured_delimited_text_lines(
                    text_content,
                    import_format=selected_format,
                    field_mapping=parsed_mapping,
                    required_fields=required_fields,
                )
            else:
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
                    "Batch mode expects one structured entry per image, but counts differ: "
                    f"found {len(images)} images and {len(entries)} structured entries. "
                    "Ensure every image has exactly one structured entry and retry."
                ),
            )
        raise HTTPException(
            status_code=400,
            detail=(
                "Batch mode expects one quote per image, but counts differ: "
                f"found {len(images)} images and {len(entries)} quotes. "
                "Ensure every image has exactly one quote and retry."
            ),
        )
    return images, entries, batch_mode


async def _prepare_regular_batch_request(
    image_dir: str,
    text_file: UploadFile | None,
    text_path: str | None,
    zones_json: str | None,
) -> tuple[list[dict[str, Any]], list[Path], list[dict[str, str]]]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    zones = _parse_zones_json(zones_json)
    text_content = await _read_text_content(text_file, text_path)
    images, entries = _paired_batch_inputs(image_dir, text_content)
    return zones, images, entries


async def _prepare_preset_batch_request(
    image_dir: str,
    text_file: UploadFile | None,
    text_path: str | None,
    preset_id: str,
    import_format: str | None = None,
    field_mapping_json: str | None = None,
) -> tuple[list[Path], list[Any], str, list[dict[str, Any]] | None]:
    if not image_dir:
        raise HTTPException(status_code=400, detail="Select an image folder for batch mode.")
    if not preset_id:
        raise HTTPException(
            status_code=400,
            detail="Choose a preset for preset-driven batch generation so the app knows how to map each text entry.",
        )

    text_content = await _read_text_content(text_file, text_path)
    images, entries, batch_mode = _paired_preset_batch_inputs(
        image_dir,
        text_content,
        preset_id,
        import_format=import_format,
        field_mapping_json=field_mapping_json,
    )
    structured_zones = build_batch_structured_zones(preset_id, config_path=PRESETS_CONFIG_PATH) if batch_mode == "structured" else None
    return images, entries, batch_mode, structured_zones


def _clamp_preview_count(sample_count: int) -> int:
    return max(1, min(sample_count, 5))


def _preview_targets(images: list[Path], entries: list[Any], sample_count: int) -> list[tuple[Path, Any]]:
    return list(zip(images, entries))[:_clamp_preview_count(sample_count)]


def _render_preset_batch_item(
    image_path: Path,
    preset_id: str,
    batch_mode: str,
    entry: Any,
    structured_zones: list[dict[str, Any]] | None,
) -> tuple[dict[str, str], bytes]:
    if batch_mode == "structured":
        if structured_zones is None:
            structured_zones = build_batch_structured_zones(preset_id, config_path=PRESETS_CONFIG_PATH)
        png_data = processor.render_from_path(
            image_path,
            name="",
            meaning="",
            zones=structured_zones,
            text_values=entry,
        )
        return (
            {
                "filename": image_path.name,
                "number": entry["number"],
                "name": entry["name"],
                "title": entry["title"],
                "subtitle": entry["subtitle"],
                "caption": entry["caption"],
            },
            png_data,
        )

    zones = build_batch_quote_zones(preset_id, str(entry), config_path=PRESETS_CONFIG_PATH)
    png_data = processor.render_from_path(image_path, name="", meaning="", zones=zones)
    return {"filename": image_path.name, "quote": str(entry)}, png_data


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
        return _preset_collection_payload()
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/presets")
async def create_preset_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Preset payload must be an object.")

    if "preset" in payload and isinstance(payload["preset"], dict):
        payload = payload["preset"]

    try:
        created = create_preset(payload, config_path=PRESETS_CONFIG_PATH)
        response = _preset_collection_payload()
        response["preset"] = created
        return response
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/presets/{preset_id}")
async def replace_preset_endpoint(preset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Preset update payload must be an object.")

    try:
        updated = update_preset(
            preset_id,
            payload,
            config_path=PRESETS_CONFIG_PATH,
            replace=True,
        )
        response = _preset_collection_payload()
        response["preset"] = updated
        return response
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/presets/{preset_id}")
async def patch_preset_endpoint(preset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Preset update payload must be an object.")

    try:
        updated = update_preset(
            preset_id,
            payload,
            config_path=PRESETS_CONFIG_PATH,
            replace=False,
        )
        response = _preset_collection_payload()
        response["preset"] = updated
        return response
    except PresetConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/presets/{preset_id}")
async def delete_preset_endpoint(preset_id: str) -> dict[str, Any]:
    try:
        removed = delete_preset(preset_id, config_path=PRESETS_CONFIG_PATH)
        response = _preset_collection_payload()
        response["preset"] = removed
        return response
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


@app.post("/api/batch/import/inspect")
async def inspect_batch_import(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    preset_id: str | None = Form(default=None),
    import_format: str | None = Form(default="auto"),
) -> dict[str, Any]:
    text_content = await _read_text_content(text_file, text_path)

    try:
        selected_format = detect_structured_import_format(text_content, import_format=import_format)
    except ProcessorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers: list[str] = []
    suggested_mapping: dict[str, str] = {}
    required_fields: list[str] = []

    if preset_id:
        try:
            required_fields = structured_fields_for_preset(preset_id, config_path=PRESETS_CONFIG_PATH)
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if selected_format in {"csv", "tsv"}:
        headers = extract_delimited_headers(text_content, import_format=selected_format)
        suggested_mapping = (
            suggest_structured_field_mapping(headers, tuple(required_fields) or ("number", "name", "caption"))
            if headers and required_fields
            else {}
        )

    return {
        "detected_format": selected_format,
        "headers": headers,
        "required_fields": required_fields,
        "suggested_mapping": suggested_mapping,
    }


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
    format: str | None = Form(default=None),
    quality: str | int | None = Form(default=None),
    export_format: str | None = Form(default=None),
    export_quality: str | int | None = Form(default=None),
    filename_template: str | None = Form(default=None),
) -> dict[str, Any]:
    zones, text_values = _resolve_single_image_render_context(preset_id, text, overlay_json)
    base_image = await _load_single_image(image, image_path)
    export_options = _parse_export_options(
        export_format or format,
        export_quality if export_quality is not None else quality,
        filename_template,
    )

    try:
        png_data = processor.render_image(base_image, name="", meaning="", zones=zones, text_values=text_values)
        source = image.filename if image and image.filename else image_path or "image"
        saved_path = save_rendered_image(
            _validate_output_dir(output_dir),
            png_data,
            source=source,
            output_format=export_options["format"],
            quality=export_options["quality"],
            filename_template=export_options["template"],
            filename_values=_resolve_export_filename_context(
                index=1,
                source=source,
                text_values=text_values,
                fallback_text=text,
                preset_id=preset_id,
            ),
        )
    except ProcessorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved_to": str(saved_path), "filename": saved_path.name}


@app.post(
    "/api/batch/preview",
    deprecated=True,
    summary="Legacy generic batch preview",
    description="Legacy compatibility route that renders batches from raw zones_json. The main UI uses the preset-aware /api/batch/quotes/preview flow.",
)
async def preview_batch(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    zones, images, entries = await _prepare_regular_batch_request(text_file=text_file, text_path=text_path, image_dir=image_dir, zones_json=zones_json)
    previews: list[dict[str, str]] = []
    for image_path, entry in _preview_targets(images, entries, sample_count):
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


@app.post(
    "/api/batch/generate",
    deprecated=True,
    summary="Legacy generic batch export",
    description="Legacy compatibility route that exports batches from raw zones_json. The main UI uses the preset-aware /api/batch/quotes/generate flow.",
)
async def generate_batch(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    zones_json: str | None = Form(default=None),
    output_dir: str = Form(default=""),
    format: str | None = Form(default=None),
    quality: str | int | None = Form(default=None),
    export_format: str | None = Form(default=None),
    export_quality: str | int | None = Form(default=None),
    preset_id: str | None = Form(default=None),
    filename_template: str | None = Form(default=None),
) -> dict[str, Any]:
    zones, images, entries = await _prepare_regular_batch_request(text_file=text_file, text_path=text_path, image_dir=image_dir, zones_json=zones_json)
    export_options = _parse_export_options(
        export_format or format,
        export_quality if export_quality is not None else quality,
        filename_template,
    )
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    for index, (image_path, entry) in enumerate(zip(images, entries), start=1):
        try:
            png_data = processor.render_from_path(image_path, entry["name"], entry["meaning"], zones)
            saved_path = save_rendered_image(
                output_root,
                png_data,
                source=image_path,
                output_format=export_options["format"],
                quality=export_options["quality"],
                filename_template=export_options["template"],
                filename_values=_resolve_export_filename_context(
                    index=index,
                    source=image_path,
                    text_values=entry,
                    preset_id=preset_id,
                ),
            )
        except ProcessorError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        files.append(str(saved_path))
    return {"saved_count": len(files), "files": files}


@app.post(
    "/api/batch/quotes/preview",
    summary="Preset-driven batch preview",
    description="Preview a preset-aware batch workflow where the selected preset controls whether entries are treated as quotes or structured fields.",
)
async def preview_batch_quotes(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    import_format: str | None = Form(default="auto"),
    field_mapping_json: str | None = Form(default=None),
    sample_count: int = Form(default=3),
) -> dict[str, Any]:
    images, entries, batch_mode, structured_zones = await _prepare_preset_batch_request(
        image_dir=image_dir,
        text_file=text_file,
        text_path=text_path,
        preset_id=preset_id,
        import_format=import_format,
        field_mapping_json=field_mapping_json,
    )
    previews: list[dict[str, str]] = []
    for image_path, entry in _preview_targets(images, entries, sample_count):
        try:
            preview, png_data = _render_preset_batch_item(
                image_path=image_path,
                preset_id=preset_id,
                batch_mode=batch_mode,
                entry=entry,
                structured_zones=structured_zones,
            )
            preview["image_b64"] = image_file_to_base64(png_data)
            previews.append(preview)
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"previews": previews, "mode": batch_mode}


@app.post(
    "/api/batch/quotes/generate",
    summary="Preset-driven batch export",
    description="Export a preset-aware batch workflow where the selected preset controls whether entries are treated as quotes or structured fields.",
)
async def generate_batch_quotes(
    text_file: UploadFile | None = File(default=None),
    text_path: str | None = Form(default=None),
    image_dir: str = Form(default=""),
    preset_id: str = Form(default=""),
    import_format: str | None = Form(default="auto"),
    field_mapping_json: str | None = Form(default=None),
    output_dir: str = Form(default=""),
    format: str | None = Form(default=None),
    quality: str | int | None = Form(default=None),
    export_format: str | None = Form(default=None),
    export_quality: str | int | None = Form(default=None),
    filename_template: str | None = Form(default=None),
) -> dict[str, Any]:
    images, entries, batch_mode, structured_zones = await _prepare_preset_batch_request(
        image_dir=image_dir,
        text_file=text_file,
        text_path=text_path,
        preset_id=preset_id,
        import_format=import_format,
        field_mapping_json=field_mapping_json,
    )
    files: list[str] = []
    output_root = _validate_output_dir(output_dir)
    export_options = _parse_export_options(
        export_format or format,
        export_quality if export_quality is not None else quality,
        filename_template,
    )

    for index, (image_path, entry) in enumerate(zip(images, entries), start=1):
        try:
            _, png_data = _render_preset_batch_item(
                image_path=image_path,
                preset_id=preset_id,
                batch_mode=batch_mode,
                entry=entry,
                structured_zones=structured_zones,
            )
            saved_path = save_rendered_image(
                output_root,
                png_data,
                source=image_path,
                output_format=export_options["format"],
                quality=export_options["quality"],
                filename_template=export_options["template"],
                filename_values=_resolve_export_filename_context(
                    index=index,
                    source=image_path,
                    text_values=entry if batch_mode == "structured" else None,
                    fallback_text=str(entry) if batch_mode != "structured" else None,
                    preset_id=preset_id,
                ),
            )
        except PresetConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ProcessorError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        files.append(str(saved_path))
    return {"saved_count": len(files), "files": files, "mode": batch_mode}
