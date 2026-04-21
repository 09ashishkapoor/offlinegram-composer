from pathlib import Path

import pytest
from PIL import Image

from presets import build_preset_zones
from processor import DEFAULT_ZONES, FONTS_DIR, ProcessorError, SkiaProcessor, parse_quote_lines


def make_sample_image(tmp_path: Path) -> Path:
    image_path = tmp_path / "sample.png"
    Image.new("RGBA", (1080, 1080), (40, 40, 40, 255)).save(image_path)
    return image_path


def test_band_zone_renders(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    output = processor.render_from_path(make_sample_image(tmp_path), "Kala Bhairava", "Guardian of time", DEFAULT_ZONES)
    assert output.startswith(b"\x89PNG\r\n\x1a\n")


def test_name_meaning_zones(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    output = processor.render_from_path(
        make_sample_image(tmp_path),
        "Kala Bhairava",
        "Protector of the sacred path",
        DEFAULT_ZONES,
    )
    assert len(output) > 500


def test_uppercase_forced(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    output = processor.render_from_path(
        make_sample_image(tmp_path),
        "kala bhairava",
        "guardian of time",
        DEFAULT_ZONES,
    )
    assert output.startswith(b"\x89PNG")


def test_long_text_wraps(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    output = processor.render_from_path(
        make_sample_image(tmp_path),
        "Kala Bhairava",
        " ".join(["The divine protector of the threshold and fearless guide."] * 6),
        DEFAULT_ZONES,
    )
    assert len(output) > 500


def test_font_fallback(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    zones = [dict(zone) for zone in DEFAULT_ZONES]
    zones[1]["font_name"] = "DefinitelyMissingFont"
    output = processor.render_from_path(make_sample_image(tmp_path), "Kala Bhairava", "Fallback font check", zones)
    assert output.startswith(b"\x89PNG")


def test_custom_text_zone(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    zones = [dict(zone) for zone in DEFAULT_ZONES]
    zones.append(
        {
            "id": "custom-zone",
            "type": "text",
            "text_source": "custom",
            "custom_text": "Om Kala Bhairavaya Namah",
            "font_name": "BebasNeue-Regular",
            "font_size": 36,
            "text_color": "#FFD700",
            "opacity": 1.0,
            "x_percent": 50,
            "y_percent": 15,
            "alignment": "center",
            "max_width_percent": 90,
            "uppercase": True,
            "bg_shape": "none",
            "bg_color": "#000000",
            "bg_opacity": 0.0,
            "bg_padding": 0,
            "shadow_enabled": True,
            "shadow_dx": 0,
            "shadow_dy": 3,
            "shadow_blur": 6,
            "shadow_color": "#000000",
            "shadow_opacity": 0.9,
            "outline_enabled": False,
            "outline_thickness": 0,
            "outline_color": "#000000",
        }
    )
    output = processor.render_from_path(make_sample_image(tmp_path), "Kala Bhairava", "Custom overlay", zones)
    assert output.startswith(b"\x89PNG")


def test_preset_1_renders_without_background_box(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    zones = build_preset_zones("preset_1", "Kala Bhairava")
    assert zones[0]["bg_shape"] == "none"
    output = processor.render_from_path(make_sample_image(tmp_path), "", "", zones)
    assert output.startswith(b"\x89PNG")


def test_preset_2_renders_with_background_box(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    zones = build_preset_zones("preset_2", "Kala Bhairava")
    assert zones[0]["bg_shape"] == "rectangle"
    output = processor.render_from_path(make_sample_image(tmp_path), "", "", zones)
    assert output.startswith(b"\x89PNG")


def test_parse_quote_lines_ignores_blank_lines():
    entries = parse_quote_lines("First quote\n\nSecond quote\n  \nThird quote\n")
    assert entries == ["First quote", "Second quote", "Third quote"]


def test_parse_quote_lines_rejects_empty_input():
    with pytest.raises(ProcessorError, match="does not contain any usable quotes"):
        parse_quote_lines("\n   \n")
