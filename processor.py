from __future__ import annotations

import base64
import ctypes
import os
import re
import string
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import skia
from PIL import Image


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
SUPPORTED_TEXT_SUFFIXES = {".txt", ".md"}
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
        "font_size": 52,
        "text_color": "#FFFFFF",
        "opacity": 1.0,
        "x_percent": 50,
        "y_percent": 67,
        "alignment": "center",
        "max_width_percent": 92,
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
        "outline_enabled": False,
        "outline_thickness": 0,
        "outline_color": "#000000",
    },
    {
        "id": "meaning-default",
        "type": "text",
        "text_source": "meaning",
        "custom_text": "",
        "font_name": "BebasNeue-Regular",
        "font_size": 35,
        "text_color": "#FFFFFF",
        "opacity": 1.0,
        "x_percent": 50,
        "y_percent": 80,
        "alignment": "center",
        "max_width_percent": 92,
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
        "outline_enabled": False,
        "outline_thickness": 0,
        "outline_color": "#000000",
    },
]


class ProcessorError(ValueError):
    pass


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
                    ("Text files", "*.txt *.md"),
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


def save_png(output_dir: str | Path, data: bytes) -> Path:
    target_dir = Path(output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / make_output_filename()
    file_path.write_bytes(data)
    return file_path.resolve()


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
    ) -> bytes:
        image = Image.open(image_path)
        return self.render_image(image, name=name, meaning=meaning, zones=zones)

    def render_image(
        self,
        image: Image.Image,
        name: str,
        meaning: str,
        zones: list[dict[str, Any]] | None = None,
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

        text_values = {"name": name, "meaning": meaning}
        for zone in active_zones:
            self._draw_zone(canvas, width, height, zone, text_values)

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
