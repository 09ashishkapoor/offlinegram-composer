from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from presets import build_preset_zones
from processor import (
    DEFAULT_ZONES,
    FONTS_DIR,
    SUPPORTED_TEXT_SUFFIXES,
    ProcessorError,
    SkiaProcessor,
    detect_structured_import_format,
    parse_field_mapping_json,
    parse_structured_delimited_text_lines,
    parse_quote_lines,
    parse_structured_text_lines,
    make_output_filename,
    save_rendered_image,
    validate_filename_template,
)


def make_sample_image(tmp_path: Path) -> Path:
    image_path = tmp_path / "sample.png"
    Image.new("RGBA", (1080, 1080), (40, 40, 40, 255)).save(image_path)
    return image_path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_size(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        return image.size


def render_preset(
    *,
    tmp_path: Path,
    preset_id: str,
    name: str = "",
    meaning: str = "",
    text_values: dict[str, str] | None = None,
) -> bytes:
    processor = SkiaProcessor(FONTS_DIR)
    zones = build_preset_zones(preset_id, "Kala Bhairava")
    return processor.render_from_path(
        make_sample_image(tmp_path),
        name,
        meaning,
        zones,
        text_values=text_values,
    )


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


def test_shipped_presets_render_with_expected_properties_and_dimensions(tmp_path: Path):
    presets = [
        "preset_1",
        "preset_2",
        (
            "preset_3",
            {"number": "1", "name": "Sphinx", "caption": "Steady wisdom at dusk"},
        ),
    ]

    for preset_id in presets:
        text_values = None
        if isinstance(preset_id, tuple):
            preset_id, text_values = preset_id

        output = render_preset(
            tmp_path=tmp_path,
            preset_id=preset_id,
            text_values=text_values,
        )

        assert output.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(output) > 5000
        assert png_size(output) == (1080, 1080)

        with Image.open(make_sample_image(tmp_path)) as source:
            source_rgb = source.convert("RGB")
        with Image.open(BytesIO(output)) as rendered:
            diff = ImageChops.difference(source_rgb, rendered.convert("RGB")).getbbox()
        assert diff is not None


def test_shipped_presets_render_outputs_are_distinct_and_reproducible(tmp_path: Path):
    def render_for(name: str) -> bytes:
        return render_preset(tmp_path=tmp_path, preset_id=name)

    preset_1_first = render_for("preset_1")
    preset_1_second = render_for("preset_1")
    preset_2 = render_for("preset_2")
    preset_3 = render_preset(
        tmp_path=tmp_path,
        preset_id="preset_3",
        text_values={"number": "1", "name": "Sphinx", "caption": "Steady wisdom at dusk"},
    )

    assert sha256_hex(preset_1_first) == sha256_hex(preset_1_second)
    assert sha256_hex(preset_1_first) != sha256_hex(preset_2)
    assert sha256_hex(preset_1_first) != sha256_hex(preset_3)
    assert sha256_hex(preset_2) != sha256_hex(preset_3)


def test_richer_text_typography_overrides_change_rendered_output(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    base = render_preset(tmp_path=tmp_path, preset_id="preset_1", text_values={"custom": "Kala Bhairava"})

    zones = build_preset_zones("preset_1", "Kala Bhairava", config_path=Path("presets.json"))
    text_zone = next(zone for zone in zones if zone.get("type") == "text")
    text_zone.update(
        {
            "text_color": "#00FF00",
            "opacity": 0.62,
            "max_width_percent": 55,
            "bg_shape": "rectangle",
            "bg_color": "#330000",
            "bg_opacity": 0.45,
            "bg_padding": 20,
            "shadow_enabled": True,
            "shadow_dx": 2,
            "shadow_dy": 2,
            "shadow_blur": 12,
            "shadow_color": "#550000",
            "shadow_opacity": 0.7,
            "outline_enabled": True,
            "outline_thickness": 4,
            "outline_color": "#FFFFFF",
        }
    )

    overridden = processor.render_from_path(
        make_sample_image(tmp_path),
        "Kala Bhairava",
        "",
        zones,
        text_values=None,
    )

    assert overridden.startswith(b"\x89PNG")
    assert sha256_hex(base) != sha256_hex(overridden)


def test_richer_overlay_render_diff_for_uppercase_and_color_path(tmp_path: Path):
    processor = SkiaProcessor(FONTS_DIR)
    base = processor.render_from_path(
        make_sample_image(tmp_path),
        "Kala Bhairava",
        "",
        build_preset_zones("preset_1", "Kala Bhairava", config_path=Path("presets.json")),
    )

    overlay_zones = build_preset_zones("preset_1", "Kala Bhairava", config_path=Path("presets.json"))
    text_zone = next(zone for zone in overlay_zones if zone.get("type") == "text")
    text_zone.update(
        {
            "uppercase": False,
            "text_color": "#ff00ff",
            "bg_color": "#000000",
            "bg_shape": "rectangle",
            "bg_padding": 24,
            "shadow_enabled": False,
            "outline_enabled": False,
        }
    )

    overridden = processor.render_from_path(make_sample_image(tmp_path), "Kala Bhairava", "", overlay_zones, text_values=None)
    assert sha256_hex(base) != sha256_hex(overridden)


def test_detect_structured_import_format_defaults_plain_structured_text_to_text():
    assert detect_structured_import_format("1. Name: Caption\n2. Other: Another") == "text"


def test_validate_filename_template_rejects_unknown_token(tmp_path: Path):
    with pytest.raises(ProcessorError, match="Unsupported filename token"):
        validate_filename_template("{index}-{bad_token}")


def test_validate_filename_template_accepts_allowed_tokens():
    assert validate_filename_template("{index}-{source}-{name}-{slug}") == "{index}-{source}-{name}-{slug}"
    assert (
        validate_filename_template("{index}_{preset}_{source_name}_{base_name}")
        == "{index}_{preset}_{source_name}_{base_name}"
    )


def test_parse_quote_lines_ignores_blank_lines():
    entries = parse_quote_lines("First quote\n\nSecond quote\n  \nThird quote\n")
    assert entries == ["First quote", "Second quote", "Third quote"]


def test_parse_quote_lines_rejects_empty_input():
    with pytest.raises(ProcessorError, match="does not contain any usable quotes"):
        parse_quote_lines("\n   \n")


def test_parse_structured_text_lines_parses_number_name_caption():
    entries = parse_structured_text_lines(
        "1. Name One: Caption first\n\n2. Name Two: Caption second"
    )
    assert entries == [
        {
            "number": "1",
            "name": "Name One",
            "title": "1",
            "subtitle": "Name One",
            "caption": "Caption first",
        },
        {
            "number": "2",
            "name": "Name Two",
            "title": "2",
            "subtitle": "Name Two",
            "caption": "Caption second",
        },
    ]


def test_parse_structured_text_lines_rejects_missing_dot():
    with pytest.raises(ProcessorError, match="must contain a '.'"):
        parse_structured_text_lines("Bad format line: missing separator")


def test_parse_structured_text_lines_rejects_missing_colon():
    with pytest.raises(ProcessorError, match="must contain a ':'"):
        parse_structured_text_lines("1. Name missing caption")


def test_parse_structured_text_lines_rejects_empty_input():
    with pytest.raises(ProcessorError, match="does not contain any usable structured entries"):
        parse_structured_text_lines("\n   \n")


def test_detect_structured_import_format_auto_prefers_csv_or_tsv():
    assert detect_structured_import_format("number,name,caption\n1,Alpha,Beta\n", None) == "csv"
    assert detect_structured_import_format("number\tname\tcaption\n1\tAlpha\tBeta\n", None) == "tsv"


def test_supported_text_suffixes_includes_csv_and_tsv():
    assert ".txt" in SUPPORTED_TEXT_SUFFIXES
    assert ".md" in SUPPORTED_TEXT_SUFFIXES
    assert ".csv" in SUPPORTED_TEXT_SUFFIXES
    assert ".tsv" in SUPPORTED_TEXT_SUFFIXES


def test_parse_structured_delimited_text_lines_with_field_to_column_mapping():
    entries, headers = parse_structured_delimited_text_lines(
        "No,Name,Description\n1,One,First caption\n",
        import_format="csv",
        required_fields=("number", "name", "caption"),
        field_mapping={"number": "No", "name": "Name", "caption": "Description"},
    )

    assert headers == ["No", "Name", "Description"]
    assert entries == [
        {
            "number": "1",
            "name": "One",
            "title": "1",
            "subtitle": "One",
            "caption": "First caption",
        }
    ]


def test_parse_structured_delimited_text_lines_with_required_field_subset():
    entries, _ = parse_structured_delimited_text_lines(
        "Name,Caption\nOne,Caption one\n",
        import_format="csv",
        required_fields=("name", "caption"),
        field_mapping={"name": "Name", "caption": "Caption"},
    )

    assert entries == [
        {
            "number": "",
            "name": "One",
            "title": "",
            "subtitle": "One",
            "caption": "Caption one",
        }
    ]


def test_parse_structured_delimited_text_lines_with_column_to_field_mapping_tsv():
    entries, _ = parse_structured_delimited_text_lines(
        "No\tName\tCaption\n2\tTwo\tSecond caption\n",
        import_format="tsv",
        required_fields=("number", "name", "caption"),
        field_mapping={"No": "number", "Name": "name", "Caption": "caption"},
    )

    assert entries[0] == {
        "number": "2",
        "name": "Two",
        "title": "2",
        "subtitle": "Two",
        "caption": "Second caption",
    }


def test_parse_field_mapping_json_validates_invalid_mapping_direction():
    with pytest.raises(ProcessorError, match="consistently map"):
        parse_field_mapping_json('{"number": "No", "No": "caption"}')


def test_parse_field_mapping_json_accepts_overlapping_column_to_field_mapping():
    mapping = parse_field_mapping_json('{"No":"number","Name":"name","Caption":"caption"}')
    assert mapping == {"number": "No", "name": "Name", "caption": "Caption"}


def test_parse_structured_delimited_text_lines_rejects_missing_required_fields():
    with pytest.raises(ProcessorError, match="Missing required structured field"):
        parse_structured_delimited_text_lines(
            "No,Name\n1,Only name missing caption\n",
            import_format="csv",
            required_fields=("number", "name", "caption"),
            field_mapping={"number": "No", "name": "Name"},
        )


def test_save_rendered_image_writes_expected_extension_and_resolves_template(tmp_path: Path):
    source_path = make_output_filename()
    sample_png = save_rendered_image(
        output_dir=tmp_path,
        data=render_preset(tmp_path=tmp_path, preset_id="preset_1", name="Name", meaning="Meaning"),
        source=source_path,
        output_format="jpg",
        quality=85,
        filename_template="{source}-{name}-{index}",
        filename_values={"name": "Hello World", "index": "1"},
    )

    assert sample_png.suffix == ".jpg"
    assert sample_png.exists()


def test_save_rendered_image_resolves_preset_and_source_alias_tokens(tmp_path: Path):
    source_path = Path("folder/source-file.png")
    sample_png = save_rendered_image(
        output_dir=tmp_path,
        data=render_preset(tmp_path=tmp_path, preset_id="preset_1", name="Name", meaning="Meaning"),
        source=source_path,
        output_format="png",
        filename_template="{index}_{preset}_{source_name}_{base_name}",
        filename_values={"index": "1", "preset": "preset_2", "source_name": "source-file"},
    )

    assert sample_png.name.startswith("1_preset_2_source-file_source-file")
    assert sample_png.suffix == ".png"


def test_save_rendered_image_sanitizes_unsafe_filename_templates(tmp_path: Path):
    sample_png = save_rendered_image(
        output_dir=tmp_path,
        data=render_preset(tmp_path=tmp_path, preset_id="preset_1", name="Name", meaning="Meaning"),
        source="source.png",
        output_format="png",
        filename_template="../bad:{preset}?/name",
        filename_values={"preset": "preset:1"},
    )

    assert sample_png.parent == tmp_path.resolve()
    assert "/" not in sample_png.name
    assert "\\" not in sample_png.name
    assert ":" not in sample_png.name
    assert "?" not in sample_png.name
    assert sample_png.exists()


def test_save_rendered_image_collides_safely_and_returns_unique_names(tmp_path: Path):
    source_path = make_output_filename()
    data = render_preset(tmp_path=tmp_path, preset_id="preset_1")

    first = save_rendered_image(
        output_dir=tmp_path,
        data=data,
        source=source_path,
        output_format="webp",
        filename_template="fixed-name",
    )
    second = save_rendered_image(
        output_dir=tmp_path,
        data=data,
        source=source_path,
        output_format="webp",
        filename_template="fixed-name",
    )

    assert first.suffix == ".webp"
    assert second.suffix == ".webp"
    assert first != second
    assert first.exists() and second.exists()


def test_render_structured_text_values_for_multiple_sources(tmp_path: Path):
    expected_first = {
        "number": "1",
        "name": "Morning Star",
        "caption": "Shine bright",
    }
    expected_second = {
        "number": "8",
        "name": "Night Owl",
        "caption": "Watch and wait",
    }

    output_a = render_preset(
        tmp_path=tmp_path,
        preset_id="preset_3",
        text_values=expected_first,
    )
    output_b = render_preset(
        tmp_path=tmp_path,
        preset_id="preset_3",
        text_values=expected_first,
    )
    output_c = render_preset(
        tmp_path=tmp_path,
        preset_id="preset_3",
        text_values=expected_second,
    )

    assert output_a.startswith(b"\x89PNG")
    assert sha256_hex(output_a) == sha256_hex(output_b)
    assert sha256_hex(output_a) != sha256_hex(output_c)
