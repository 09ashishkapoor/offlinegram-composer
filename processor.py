from __future__ import annotations

import base64
import ctypes
import csv
import os
import re
import string
import json
from collections.abc import Mapping
from io import StringIO
from io import BytesIO
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import skia
from PIL import Image


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
_BATCH_QUOTE_FILE_SUFFIXES = (".txt", ".md", ".csv", ".tsv")
SUPPORTED_TEXT_SUFFIXES = set(_BATCH_QUOTE_FILE_SUFFIXES)
_BATCH_QUOTE_FILE_PATTERNS = " ".join(f"*{ext}" for ext in _BATCH_QUOTE_FILE_SUFFIXES)
FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}
DEFAULT_FONT_FILE = "BebasNeue-Regular.ttf"
NATIVE_PICKER_MODES = {"image", "output", "batch-images", "batch-quotes", "batch-output"}

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"
TEMP_DIR = BASE_DIR / "temp"
UPLOADS_DIR = TEMP_DIR / "uploads"
PREVIEW_DIR = TEMP_DIR / "out"

DEFAULT_ZONES: list[dict[str, Any]] = [
    {
        "id": "band-default",
        "type": "band",
        "bg_shape": "full_width_band",
        "bg_color": "#000000",
        "bg_opacity": 0.8,
        "band_height_percent": 35,
    },
    {
        "id": "name-default",
        "type": "text",
        "text_source": "name",
        "custom_text": "",
        "font_name": "BebasNeue-Regular",
        "font_size": 58,
        "text_color": "#FFFFFF",
        "opacity": 1.0,
        "x_percent": 50,
        "y_percent": 70,
        "alignment": "center",
        "max_width_percent": 86,
        "uppercase": True,
        "bg_shape": "none",
        "bg_color": "#000000",
        "bg_opacity": 0.0,
        "bg_padding": 0,
        "shadow_enabled": True,
        "shadow_dx": 0,
        "shadow_dy": 4,
        "shadow_blur": 8,
        "shadow_color": "#000000",
        "shadow_opacity": 0.9,
        "outline_enabled": True,
        "outline_thickness": 8,
        "outline_color": "#000000",
    },
    {
        "id": "meaning-default",
        "type": "text",
        "text_source": "meaning",
        "custom_text": "",
        "font_name": "BebasNeue-Regular",
        "font_size": 39,
        "text_color": "#FFFFFF",
        "opacity": 1.0,
        "x_percent": 50,
        "y_percent": 82,
        "alignment": "center",
        "max_width_percent": 84,
        "uppercase": True,
        "bg_shape": "none",
        "bg_color": "#000000",
        "bg_opacity": 0.0,
        "bg_padding": 0,
        "shadow_enabled": True,
        "shadow_dx": 0,
        "shadow_dy": 4,
        "shadow_blur": 8,
        "shadow_color": "#000000",
        "shadow_opacity": 0.9,
        "outline_enabled": True,
        "outline_thickness": 6,
        "outline_color": "#000000",
    },
]

STRUCTURED_TEXT_FIELDS = ("number", "name", "title", "subtitle", "caption")
DEFAULT_REQUIRED_STRUCTURED_FIELDS = ("number", "name", "caption")


class ProcessorError(ValueError):
    pass


ALLOWED_EXPORT_FORMATS = {"png", "jpg", "webp"}
LOSSY_EXPORT_FORMATS = {"jpg", "webp"}
_TEMPLATE_TOKEN_PATTERN = re.compile(r"{(\w+)}")


def normalize_export_format(raw_format: str | None) -> str:
    value = (raw_format or "png").strip().lower().lstrip(".")
    if value == "jpeg":
        value = "jpg"
    if value not in ALLOWED_EXPORT_FORMATS:
        raise ProcessorError("Unsupported export format. Supported formats are PNG, JPG, and WebP.")
    return value


def validate_export_quality(export_format: str, quality: int | None) -> int | None:
    if export_format not in LOSSY_EXPORT_FORMATS:
        return None

    if quality is None:
        return 90

    if not isinstance(quality, int):
        raise ProcessorError("Quality must be an integer between 1 and 100.")

    if not (1 <= quality <= 100):
        raise ProcessorError("Quality must be between 1 and 100.")
    return quality


def validate_filename_template(template: str | None) -> str:
    raw = (template or "").strip()
    if not raw:
        return "export-{index}"

    if raw.count("{") != raw.count("}"):
        raise ProcessorError("Invalid filename template: mismatched template braces.")

    matches = _TEMPLATE_TOKEN_PATTERN.findall(raw)
    token_start = raw.find("{")
    if token_start != -1:
        allowed_tokens = {"index", "source", "source_name", "base_name", "name", "slug", "preset"}
        for token in matches:
            if token not in allowed_tokens:
                raise ProcessorError(
                    "Unsupported filename token. Allowed tokens are: {index}, {source}, {source_name}, {base_name}, {name}, {slug}, {preset}."
                )
        # If there is a brace, ensure every brace pair belongs to an allowed token.
        # This also rejects things like `{foo` or `}` without `{` in the malformed case above.
        sanitized = re.sub(_TEMPLATE_TOKEN_PATTERN, "", raw)
        if "{" in sanitized or "}" in sanitized:
            raise ProcessorError("Invalid filename template syntax.")

    if not raw:
        return "export-{index}"

    return raw


def _sanitize_token_value(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return "untitled"
    text = text.replace("/", " ").replace("\\", " ")
    text = re.sub(r'[:*?"<>|]+', " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ._")
    return text or "untitled"


def _slugify(value: Any) -> str:
    text = _sanitize_token_value(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def _resolve_filename_tokens(values: Mapping[str, Any]) -> dict[str, str]:
    source_seed = values.get("source_name") or values.get("base_name") or values.get("source") or "image"
    source_stem = Path(str(source_seed)).stem or "image"
    source_value = _sanitize_token_value(source_stem)
    name_value = _sanitize_token_value(values.get("name", ""))
    index_value = str(values.get("index", "1")).strip() or "1"
    preset_value = _sanitize_token_value(values.get("preset", ""))

    return {
        "source": source_value,
        "source_name": source_value,
        "base_name": source_value,
        "name": name_value,
        "slug": _slugify(name_value),
        "preset": preset_value,
        "index": index_value,
    }


def resolve_output_filename(template: str, values: Mapping[str, Any]) -> str:
    resolved_tokens = _resolve_filename_tokens(values)

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        return resolved_tokens[token]

    resolved = _TEMPLATE_TOKEN_PATTERN.sub(replace, template)
    resolved = re.sub(r"[\\/]+", "-", resolved)
    resolved = re.sub(r'[:*?"<>|]+', "-", resolved)
    resolved = resolved.replace("..", "-")
    resolved = re.sub(r"\s+", " ", resolved).strip(" .-")
    return resolved or "export"


def _ensure_path_unique(base_path: Path, candidate: str) -> Path:
    candidate_path = base_path / candidate
    stem = candidate_path.stem
    suffix = candidate_path.suffix

    if not candidate_path.exists():
        return candidate_path

    for index in range(2, 10000):
        candidate_with_suffix = f"{stem}-{index}{suffix}"
        path = base_path / candidate_with_suffix
        if not path.exists():
            return path

    raise ProcessorError("Could not find a unique filename in the selected output directory.")


def ensure_runtime_dirs() -> None:
    for path in (TEMP_DIR, UPLOADS_DIR, PREVIEW_DIR):
        path.mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(max_age_seconds: int = 3600) -> None:
    ensure_runtime_dirs()
    now = time.time()
    for folder in (UPLOADS_DIR, PREVIEW_DIR):
        for item in folder.glob("*"):
            try:
                if item.is_file() and now - item.stat().st_mtime > max_age_seconds:
                    item.unlink()
            except OSError:
                continue


def normalize_zones(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return [dict(zone) for zone in DEFAULT_ZONES]
    return [dict(zone) for zone in raw]


def parse_text_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            name, meaning = line.split(":", 1)
            entries.append({"name": name.strip(), "meaning": meaning.strip()})
        else:
            entries.append({"name": line, "meaning": ""})
    if not entries:
        raise ProcessorError("The text file does not contain any usable entries.")
    return entries


def parse_quote_lines(text: str) -> list[str]:
    quotes = [line.strip() for line in text.splitlines() if line.strip()]
    if not quotes:
        raise ProcessorError("The text file does not contain any usable quotes.")
    return quotes


def parse_structured_text_lines(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        number, number_separator, remainder = line.partition(".")
        if not number_separator:
            raise ProcessorError(
                f"Line {line_number} must contain a '.' separating the number and name fields."
            )

        name, caption_separator, caption = remainder.partition(":")
        if not caption_separator:
            raise ProcessorError(
                f"Line {line_number} must contain a ':' separating the name and caption fields."
            )

        number = number.strip()
        name = name.strip()
        caption = caption.strip()
        if not number or not name or not caption:
            raise ProcessorError(
                f"Line {line_number} must include number, name, and caption text."
            )

        entries.append(
            {
                "number": number,
                "name": name,
                "title": number,
                "subtitle": name,
                "caption": caption,
            }
        )

    if not entries:
        raise ProcessorError("The text file does not contain any usable structured entries.")
    return entries


def detect_structured_import_format(text: str, import_format: str | None = None) -> str:
    """Return one of 'csv', 'tsv', or 'text'."""
    requested = (import_format or "auto").strip().lower()
    if requested == "auto":
        requested = "auto"
    if requested not in {"auto", "text", "csv", "tsv"}:
        raise ProcessorError("import_format must be one of 'auto', 'text', 'csv', or 'tsv'.")

    if requested == "text":
        return "text"
    if requested == "csv":
        return "csv"
    if requested == "tsv":
        return "tsv"

    sample_lines = [line for line in text.splitlines() if line.strip()]
    if not sample_lines:
        return "text"

    sample = "\n".join(sample_lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
        if dialect.delimiter == "\t":
            return "tsv"
        if dialect.delimiter == ",":
            return "csv"
    except csv.Error:
        pass

    has_tab = "\t" in sample
    has_comma = "," in sample
    if has_tab and not has_comma:
        return "tsv"
    if has_comma and not has_tab:
        return "csv"

    first = sample_lines[0]
    if "," in first and "\t" not in first:
        return "csv"
    if "\t" in first and "," not in first:
        return "tsv"

    return "text"


def _normalize_column_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", value.strip().lower())
    return normalized


def _default_field_aliases() -> dict[str, str]:
    return {
        "number": "number",
        "num": "number",
        "no": "number",
        "#": "number",
        "name": "name",
        "deity": "name",
        "text": "name",
        "caption": "caption",
        "subheading": "subtitle",
        "subtitle": "subtitle",
        "title": "title",
    }


def parse_field_mapping_json(mapping_json: str | None) -> dict[str, str]:
    """Parse a user-provided field mapping.

    Supports both of:
    - {"number": "No", "name": "Name", "caption": "Caption"}
    - {"No": "number", "Name": "name", "Caption": "caption"}
    """
    if not mapping_json:
        return {}

    try:
        payload = json.loads(mapping_json)
    except json.JSONDecodeError as exc:
        raise ProcessorError("Invalid field mapping JSON.") from exc

    if not isinstance(payload, dict):
        raise ProcessorError("Field mapping JSON must be an object.")

    if not payload:
        return {}

    fields_to_columns: dict[str, str] = {}
    columns_to_fields: dict[str, str] = {}
    ambiguous_pairs: list[tuple[str, str, str, str]] = []
    map_field_to_column: bool | None = None

    for raw_key, raw_value in payload.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise ProcessorError("Field mapping JSON must map string names to string names.")

        key = raw_key.strip()
        value = raw_value.strip()
        if not key or not value:
            raise ProcessorError("Field mapping JSON must be non-empty strings.")

        normalized_key = _normalize_column_name(key)
        normalized_value = _normalize_column_name(value)

        key_is_field = normalized_key in STRUCTURED_TEXT_FIELDS
        value_is_field = normalized_value in STRUCTURED_TEXT_FIELDS

        if key_is_field and not value_is_field:
            if map_field_to_column is False:
                raise ProcessorError("Field mapping must consistently map either field->column or column->field.")
            fields_to_columns[normalized_key] = value
            map_field_to_column = True
            continue

        if value_is_field and not key_is_field:
            if map_field_to_column is True:
                raise ProcessorError("Field mapping must consistently map either field->column or column->field.")
            columns_to_fields[key] = normalized_value
            map_field_to_column = False
            continue

        if key_is_field and value_is_field:
            ambiguous_pairs.append((key, value, normalized_key, normalized_value))
            continue

        raise ProcessorError(
            "Field mapping must use structured fields ('number', 'name', 'title', 'subtitle', 'caption') "
            "as keys or values."
        )

    if map_field_to_column is None and ambiguous_pairs:
        map_field_to_column = True

    if map_field_to_column is False:
        for key, _value, _normalized_key, normalized_value in ambiguous_pairs:
            columns_to_fields[key] = normalized_value

    if map_field_to_column is True:
        for _, value, normalized_key, _normalized_value in ambiguous_pairs:
            fields_to_columns[normalized_key] = value

    if fields_to_columns and columns_to_fields:
        raise ProcessorError("Field mapping must consistently map either field->column or column->field.")

    if columns_to_fields:
        # Invert into field->column
        return {field: column for column, field in columns_to_fields.items()}
    return fields_to_columns


def extract_delimited_headers(text: str, *, import_format: str) -> list[str]:
    delimiter = "," if import_format == "csv" else "\t"
    reader = csv.DictReader(StringIO(text), delimiter=delimiter)
    return list(reader.fieldnames or [])


def parse_structured_delimited_text_lines(
    text: str,
    *,
    import_format: str,
    field_mapping: dict[str, str] | None = None,
    required_fields: tuple[str, ...] = DEFAULT_REQUIRED_STRUCTURED_FIELDS,
) -> tuple[list[dict[str, str]], list[str]]:
    required_fields = required_fields or DEFAULT_REQUIRED_STRUCTURED_FIELDS
    delimiter = "," if import_format == "csv" else "\t"
    reader = csv.DictReader(StringIO(text), delimiter=delimiter)

    headers = reader.fieldnames or []
    if not headers:
        raise ProcessorError("The file does not contain a valid header row for csv/tsv import.")

    header_index = {_normalize_column_name(header): header for header in headers}
    resolved_mapping = dict(field_mapping or {})

    aliases = _default_field_aliases()
    entries: list[dict[str, str]] = []

    for field in required_fields:
        mapped = resolved_mapping.get(field)
        if mapped:
            normalized_mapped = _normalize_column_name(mapped)
            if normalized_mapped not in header_index:
                raise ProcessorError(f"Mapped column '{mapped}' for field '{field}' was not found in the file header.")
        else:
            # Best-effort auto-detect from header aliases/standard names.
            normalized_target_field = _normalize_column_name(field)
            alias_candidate: str | None = None
            for normalized_header, original_header in header_index.items():
                if normalized_header == normalized_target_field:
                    alias_candidate = original_header
                    break
                if aliases.get(normalized_header) == field:
                    alias_candidate = original_header
                    break
            if alias_candidate is None:
                raise ProcessorError(
                    f"Missing required structured field '{field}' in csv/tsv import. "
                    f"Provide a field mapping for {', '.join(required_fields)}."
                )
            resolved_mapping[field] = alias_candidate

    for raw_row in reader:
        if raw_row is None:
            continue

        values: dict[str, str] = {}
        for key, value in raw_row.items():
            values[key or ""] = "" if value is None else str(value).strip()

        if not any(values.values()):
            continue

        number = values.get(resolved_mapping.get("number", ""), "")
        name = values.get(resolved_mapping.get("name", ""), "")
        caption = values.get(resolved_mapping.get("caption", ""), "")
        missing_required_values = [field for field in required_fields if not values.get(resolved_mapping.get(field, ""), "")]
        if missing_required_values:
            raise ProcessorError(
                "Each csv/tsv row must provide "
                + ", ".join(missing_required_values)
                + " values."
            )

        title = values.get(resolved_mapping.get("title", ""), number)
        subtitle = values.get(resolved_mapping.get("subtitle", ""), name)

        entries.append(
            {
                "number": number,
                "name": name,
                "title": title,
                "subtitle": subtitle,
                "caption": caption,
            }
        )

    if not entries:
        raise ProcessorError("The file does not contain any usable structured entries.")

    return entries, headers


def suggest_structured_field_mapping(headers: list[str], required_fields: tuple[str, ...] = DEFAULT_REQUIRED_STRUCTURED_FIELDS) -> dict[str, str]:
    aliases = _default_field_aliases()
    header_lookup = {_normalize_column_name(header): header for header in headers}
    mapping: dict[str, str] = {}
    for field in required_fields:
        normalized_field = _normalize_column_name(field)
        if normalized_field in header_lookup:
            mapping[field] = header_lookup[normalized_field]
            continue

        for normalized_header, original_header in header_lookup.items():
            if aliases.get(normalized_header) == field:
                mapping[field] = original_header
                break

    return mapping


def list_font_choices(fonts_dir: Path = FONTS_DIR) -> list[dict[str, str]]:
    if not fonts_dir.exists():
        return []
    fonts = [
        {
            "name": file.stem,
            "filename": file.name,
        }
        for file in sorted(fonts_dir.iterdir(), key=lambda item: item.name.lower())
        if file.is_file() and file.suffix.lower() in FONT_SUFFIXES
    ]
    return fonts


def list_images(directory: str | Path) -> list[Path]:
    target = Path(directory).expanduser().resolve(strict=True)
    if not target.is_dir():
        raise ProcessorError(f"{target} is not a directory.")
    return [
        file
        for file in sorted(target.iterdir(), key=lambda item: item.name.lower())
        if file.is_file() and file.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    ]


def list_windows_roots() -> list[str]:
    if os.name != "nt":
        return ["/"]
    roots: list[str] = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive = f"{letter}:\\"
            if Path(drive).exists():
                roots.append(drive)
        bitmask >>= 1
    return roots


def browse_directory(path: str | None) -> dict[str, Any]:
    if not path:
        return {
            "current": None,
            "parent": None,
            "roots": list_windows_roots(),
            "folders": [],
            "images": [],
            "text_files": [],
        }

    try:
        current = Path(path).expanduser().resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ProcessorError(f"Unable to browse '{path}'.") from exc

    if not current.is_dir():
        raise ProcessorError(f"{current} is not a directory.")

    folders = [
        {"name": item.name, "path": str(item)}
        for item in sorted(current.iterdir(), key=lambda child: child.name.lower())
        if item.is_dir()
    ]
    images = [
        {"name": item.name, "path": str(item)}
        for item in sorted(current.iterdir(), key=lambda child: child.name.lower())
        if item.is_file() and item.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    ]
    text_files = [
        {"name": item.name, "path": str(item)}
        for item in sorted(current.iterdir(), key=lambda child: child.name.lower())
        if item.is_file() and item.suffix.lower() in SUPPORTED_TEXT_SUFFIXES
    ]
    parent = None if current.parent == current else str(current.parent)
    return {
        "current": str(current),
        "parent": parent,
        "roots": list_windows_roots(),
        "folders": folders,
        "images": images,
        "text_files": text_files,
    }


def _resolve_initial_directory(initial_path: str | None) -> str | None:
    if not initial_path:
        return None

    try:
        candidate = Path(initial_path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return None

    if candidate.exists() and candidate.is_file():
        candidate = candidate.parent

    if candidate.exists() and candidate.is_dir():
        return str(candidate)

    parent = candidate.parent
    if parent.exists() and parent.is_dir():
        return str(parent)
    return None


def pick_native_path(mode: str, initial_path: str | None = None) -> str | None:
    if os.name != "nt":
        raise ProcessorError("Native path picker is available only on Windows.")

    if mode not in NATIVE_PICKER_MODES:
        raise ProcessorError(f"Unsupported picker mode '{mode}'.")

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise ProcessorError("Native path picker is unavailable because tkinter is missing.") from exc

    initial_dir = _resolve_initial_directory(initial_path)
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()

    try:
        if mode == "image":
            selected = filedialog.askopenfilename(
                title="Choose Image",
                initialdir=initial_dir,
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                    ("All files", "*.*"),
                ],
            )
        elif mode == "batch-quotes":
            selected = filedialog.askopenfilename(
                title="Choose Batch Quote File",
                initialdir=initial_dir,
                filetypes=[
                    ("Text files", _BATCH_QUOTE_FILE_PATTERNS),
                    ("All files", "*.*"),
                ],
            )
        else:
            titles = {
                "output": "Choose Output Folder",
                "batch-images": "Choose Batch Image Folder",
                "batch-output": "Choose Batch Output Folder",
            }
            selected = filedialog.askdirectory(
                title=titles.get(mode, "Choose Folder"),
                initialdir=initial_dir,
                mustexist=True,
            )
    finally:
        root.destroy()

    if not selected:
        return None

    try:
        resolved = Path(selected).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProcessorError("Selected path is no longer available.") from exc
    return str(resolved)


def make_output_filename() -> str:
    return f"{uuid.uuid4()}.png"


def _decode_rendered_image(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    return image


def _prepare_image_for_format(image: Image.Image, output_format: str) -> Image.Image:
    if output_format == "jpg":
        if image.mode in {"RGBA", "LA"}:
            rgb_canvas = Image.new("RGB", image.size, (255, 255, 255))
            rgb_canvas.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
            return rgb_canvas
        return image.convert("RGB")

    if image.mode != "RGBA":
        return image.convert("RGBA")
    return image


def save_rendered_image(
    output_dir: str | Path,
    data: bytes,
    *,
    source: str | Path = "image",
    output_format: str = "png",
    quality: int | None = None,
    filename_template: str | None = None,
    filename_values: Mapping[str, Any] | None = None,
) -> Path:
    target_dir = Path(output_dir).expanduser()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ProcessorError("Unable to prepare the selected output folder.") from exc

    template = validate_filename_template(filename_template)
    source_stem = Path(str(source)).stem if source else "image"
    resolved_values: dict[str, Any] = {
        "index": "1",
        "source": source_stem,
        "source_name": source_stem,
        "base_name": source_stem,
        "name": "",
        "preset": "",
    }
    if filename_values:
        resolved_values.update(dict(filename_values))
    resolved_filename = resolve_output_filename(template, resolved_values)

    output_format = normalize_export_format(output_format)
    output_quality = validate_export_quality(output_format, quality)

    final_filename = _ensure_path_unique(target_dir, f"{resolved_filename}.{output_format if output_format != 'jpg' else 'jpg'}")

    image = _decode_rendered_image(data)
    prepared = _prepare_image_for_format(image, output_format)

    with BytesIO() as output_buffer:
        if output_format == "png":
            prepared.save(output_buffer, format="PNG")
        elif output_format == "jpg":
            prepared.save(
                output_buffer,
                format="JPEG",
                quality=output_quality or 90,
                optimize=True,
            )
        elif output_format == "webp":
            prepared.save(
                output_buffer,
                format="WEBP",
                quality=output_quality or 80,
                method=6,
                lossless=False,
            )
        else:
            raise ProcessorError("Unsupported export format.")

        try:
            final_filename.write_bytes(output_buffer.getvalue())
        except OSError as exc:
            raise ProcessorError("Unable to write the exported image to the selected output folder.") from exc

    return final_filename.resolve()


def save_png(
    output_dir: str | Path,
    data: bytes,
    *,
    source: str | Path = "image",
    filename_template: str | None = None,
    filename_values: Mapping[str, Any] | None = None,
) -> Path:
    return save_rendered_image(
        output_dir,
        data,
        source=source,
        output_format="png",
        filename_template=filename_template,
        filename_values=filename_values,
    )


def image_file_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


class SkiaProcessor:
    def __init__(self, fonts_dir: Path = FONTS_DIR) -> None:
        self.fonts_dir = Path(fonts_dir)
        self._font_cache: dict[tuple[str, int], skia.Font] = {}

    def render_from_path(
        self,
        image_path: str | Path,
        name: str,
        meaning: str,
        zones: list[dict[str, Any]] | None = None,
        text_values: dict[str, str] | None = None,
    ) -> bytes:
        image = Image.open(image_path)
        return self.render_image(image, name=name, meaning=meaning, zones=zones, text_values=text_values)

    def render_image(
        self,
        image: Image.Image,
        name: str,
        meaning: str,
        zones: list[dict[str, Any]] | None = None,
        text_values: dict[str, str] | None = None,
    ) -> bytes:
        active_zones = normalize_zones(zones)
        base_image = image.convert("RGBA")
        width, height = base_image.size
        surface = skia.Surface(width, height)
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorBLACK)
        rgba_array = np.array(base_image)
        bgra_array = np.ascontiguousarray(rgba_array[:, :, [2, 1, 0, 3]])  # RGBA -> BGRA (Skia native order)
        canvas.drawImage(skia.Image.fromarray(bgra_array), 0, 0)

        resolved_text_values = {"name": name, "meaning": meaning}
        if text_values:
            resolved_text_values.update({str(key): str(value) for key, value in text_values.items()})
        for zone in active_zones:
            self._draw_zone(canvas, width, height, zone, resolved_text_values)

        snapshot = surface.makeImageSnapshot()
        data = snapshot.encodeToData()
        if data is None:
            raise ProcessorError("Failed to encode PNG output.")
        return bytes(data)

    def _draw_zone(
        self,
        canvas: skia.Canvas,
        width: int,
        height: int,
        zone: dict[str, Any],
        text_values: dict[str, str],
    ) -> None:
        zone_type = zone.get("type", "text")
        shape = zone.get("bg_shape", "none")

        if zone_type == "band" or shape == "full_width_band":
            self._draw_band(canvas, width, height, zone)
            if zone_type == "band":
                return

        text = self._resolve_zone_text(zone, text_values)
        if not text:
            return

        font_size = int(zone.get("font_size", 48))
        font = self._get_font(str(zone.get("font_name", DEFAULT_FONT_FILE)), font_size)
        metrics = font.getMetrics()
        line_height = max(
            1.0,
            float(metrics.fDescent - metrics.fAscent + metrics.fLeading),
        )
        max_width = self._resolve_max_width(zone, width)
        lines = self._wrap_text(text, font, max_width)
        if not lines:
            return

        x_percent = float(zone.get("x_percent", 50))
        y_percent = float(zone.get("y_percent", 50))
        alignment = str(zone.get("alignment", "center")).lower()
        center_x = width * (x_percent / 100.0)
        center_y = height * (y_percent / 100.0)
        line_widths = [float(font.measureText(line)) for line in lines]
        max_line_width = max(line_widths)
        total_height = line_height * len(lines)
        block_top = center_y - (total_height / 2.0)
        baseline_start = block_top - float(metrics.fAscent)

        if shape in {"rectangle", "rounded_rectangle"}:
            self._draw_text_background(
                canvas=canvas,
                zone=zone,
                center_x=center_x,
                center_y=center_y,
                alignment=alignment,
                max_line_width=max_line_width,
                total_height=total_height,
            )

        for index, line in enumerate(lines):
            line_width = line_widths[index]
            draw_x = self._resolve_line_x(center_x, line_width, alignment)
            draw_y = baseline_start + (index * line_height)
            self._draw_text_line(canvas, zone, font, line, draw_x, draw_y)

    def _draw_band(self, canvas: skia.Canvas, width: int, height: int, zone: dict[str, Any]) -> None:
        band_height_percent = float(zone.get("band_height_percent", 35))
        band_height = height * (band_height_percent / 100.0)
        band_top = height - band_height
        color = self._color_to_int(
            zone.get("bg_color", "#000000"),
            float(zone.get("bg_opacity", 0.8)),
        )
        paint = skia.Paint(Color=color, AntiAlias=True)
        canvas.drawRect(skia.Rect.MakeXYWH(0, band_top, width, band_height), paint)

    def _draw_text_background(
        self,
        canvas: skia.Canvas,
        zone: dict[str, Any],
        center_x: float,
        center_y: float,
        alignment: str,
        max_line_width: float,
        total_height: float,
    ) -> None:
        padding = float(zone.get("bg_padding", 0))
        rect_width = max_line_width + (padding * 2)
        rect_height = total_height + (padding * 2)
        if alignment == "left":
            left = center_x - padding
        elif alignment == "right":
            left = center_x - rect_width + padding
        else:
            left = center_x - (rect_width / 2)
        top = center_y - (rect_height / 2)
        rect = skia.Rect.MakeXYWH(left, top, rect_width, rect_height)
        paint = skia.Paint(
            Color=self._color_to_int(
                zone.get("bg_color", "#000000"),
                float(zone.get("bg_opacity", 0.0)),
            ),
            AntiAlias=True,
        )
        shape = zone.get("bg_shape", "none")
        if shape == "rounded_rectangle":
            canvas.drawRoundRect(rect, 18, 18, paint)
        else:
            canvas.drawRect(rect, paint)

    def _draw_text_line(
        self,
        canvas: skia.Canvas,
        zone: dict[str, Any],
        font: skia.Font,
        line: str,
        x: float,
        y: float,
    ) -> None:
        fill_paint = skia.Paint(
            AntiAlias=True,
            Color=self._color_to_int(
                zone.get("text_color", "#FFFFFF"),
                float(zone.get("opacity", 1.0)),
            ),
        )
        if zone.get("shadow_enabled", False):
            blur = float(zone.get("shadow_blur", 8))
            fill_paint.setImageFilter(
                skia.ImageFilters.DropShadow(
                    float(zone.get("shadow_dx", 0)),
                    float(zone.get("shadow_dy", 4)),
                    blur,
                    blur,
                    self._color_to_int(
                        zone.get("shadow_color", "#000000"),
                        float(zone.get("shadow_opacity", 0.9)),
                    ),
                )
            )

        if zone.get("outline_enabled", False) and float(zone.get("outline_thickness", 0)) > 0:
            outline_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=float(zone.get("outline_thickness", 1)),
                Color=self._color_to_int(zone.get("outline_color", "#000000"), 1.0),
            )
            canvas.drawString(line, x, y, font, outline_paint)

        canvas.drawString(line, x, y, font, fill_paint)

    def _resolve_zone_text(self, zone: dict[str, Any], text_values: dict[str, str]) -> str:
        source = zone.get("text_source", "custom")
        if source == "custom":
            text = str(zone.get("custom_text", ""))
        else:
            text = text_values.get(str(source), "")
        text = text.strip()
        if zone.get("uppercase", True):
            text = text.upper()
        return text

    def _resolve_max_width(self, zone: dict[str, Any], image_width: int) -> float:
        if zone.get("max_width"):
            return float(zone["max_width"])
        return image_width * (float(zone.get("max_width_percent", 92)) / 100.0)

    def _resolve_line_x(self, center_x: float, line_width: float, alignment: str) -> float:
        if alignment == "left":
            return center_x
        if alignment == "right":
            return center_x - line_width
        return center_x - (line_width / 2.0)

    def _resolve_font_path(self, font_name: str) -> Path | None:
        if not self.fonts_dir.exists():
            return None

        requested = Path(font_name).name
        candidates = [self.fonts_dir / requested]
        if Path(requested).suffix:
            stem = Path(requested).stem
        else:
            stem = requested
            for suffix in FONT_SUFFIXES:
                candidates.append(self.fonts_dir / f"{requested}{suffix}")

        for file in self.fonts_dir.iterdir():
            if not file.is_file() or file.suffix.lower() not in FONT_SUFFIXES:
                continue
            if file.name.lower() == requested.lower() or file.stem.lower() == stem.lower():
                return file

        for candidate in candidates:
            if candidate.exists():
                return candidate

        default_path = self.fonts_dir / DEFAULT_FONT_FILE
        if default_path.exists():
            return default_path

        available = list_font_choices(self.fonts_dir)
        return self.fonts_dir / available[0]["filename"] if available else None

    def _get_font(self, font_name: str, size: int) -> skia.Font:
        cache_key = (font_name.lower(), size)
        cached = self._font_cache.get(cache_key)
        if cached is not None:
            return cached

        font_path = self._resolve_font_path(font_name)
        if font_path is not None:
            typeface = skia.Typeface.MakeFromFile(str(font_path))
            if typeface is not None:
                font = skia.Font(typeface, size)
                self._font_cache[cache_key] = font
                return font

        font = skia.Font(None, size)
        self._font_cache[cache_key] = font
        return font

    def _wrap_text(self, text: str, font: skia.Font, max_width: float) -> list[str]:
        sentence_chunks = re.split(r"([.!?]\s+)", text)
        sentences: list[str] = []
        for index in range(0, len(sentence_chunks), 2):
            sentence = sentence_chunks[index]
            if index + 1 < len(sentence_chunks):
                sentence += sentence_chunks[index + 1].strip()
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)

        if len(sentences) <= 1:
            return self._wrap_words(text, font, max_width)

        lines: list[str] = []
        for sentence in sentences:
            if font.measureText(sentence) <= max_width:
                lines.append(sentence)
            else:
                lines.extend(self._wrap_words(sentence, font, max_width))
        return lines

    def _wrap_words(self, text: str, font: skia.Font, max_width: float) -> list[str]:
        words = text.split()
        if not words:
            return []
        lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join([*current, word])
            if current and font.measureText(candidate) > max_width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        return lines

    def _color_to_int(self, color_value: Any, opacity: float) -> int:
        text = str(color_value).strip().lstrip("#")
        if len(text) != 6:
            text = "FFFFFF"
        red = int(text[0:2], 16)
        green = int(text[2:4], 16)
        blue = int(text[4:6], 16)
        alpha = max(0, min(255, int(opacity * 255)))
        return skia.ColorSetARGB(alpha, red, green, blue)
