import json
from pathlib import Path

import pytest

from presets import (
    PresetConfigError,
    build_batch_quote_zones,
    build_batch_structured_zones,
    build_preset_zones,
    create_preset,
    delete_preset,
    list_presets,
    update_preset,
    resolve_batch_preset_mode,
)


def write_config(path: Path) -> Path:
    path.write_text(
        """
{
  "presets": [
    {
      "id": "preset_1",
      "label": "Preset 1",
      "description": "Centered impact text with outline and shadow",
      "zones": [
        {
          "id": "preset-1-text",
          "type": "text",
          "text_source": "custom",
          "custom_text": "",
          "font_name": "BebasNeue-Regular",
          "font_size": 64,
          "text_color": "#FFFFFF",
          "opacity": 1.0,
          "x_percent": 50,
          "y_percent": 50,
          "alignment": "center",
          "max_width_percent": 82,
          "uppercase": true,
          "bg_shape": "none",
          "bg_color": "#000000",
          "bg_opacity": 0.0,
          "bg_padding": 0,
          "shadow_enabled": true,
          "shadow_dx": 0,
          "shadow_dy": 5,
          "shadow_blur": 14,
          "shadow_color": "#000000",
          "shadow_opacity": 0.9,
          "outline_enabled": true,
          "outline_thickness": 8,
          "outline_color": "#000000"
        }
      ]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    return path


def test_list_presets_returns_metadata(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")
    presets = list_presets(config_path)
    assert presets == [
        {
            "id": "preset_1",
            "label": "Preset 1",
            "description": "Centered impact text with outline and shadow",
        }
    ]


def test_build_preset_zones_injects_user_text(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")
    zones = build_preset_zones("preset_1", "Kala Bhairava", config_path=config_path)
    assert zones[0]["custom_text"] == "Kala Bhairava"
    assert zones[0]["uppercase"] is True
    assert zones[0]["outline_thickness"] == 8


def test_build_preset_zones_rejects_missing_preset(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")
    with pytest.raises(PresetConfigError):
        build_preset_zones("missing", "Text", config_path=config_path)


def test_list_presets_returns_three_launch_presets(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")
    presets = list_presets(config_path)
    assert [preset["id"] for preset in presets] == ["preset_1", "preset_2", "preset_3"]


def test_resolve_batch_preset_mode_detects_quote_and_structured_modes(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert resolve_batch_preset_mode("preset_1", config_path=config_path) == "quote"
    assert resolve_batch_preset_mode("preset_3", config_path=config_path) == "structured"


def test_resolve_batch_preset_mode_rejects_invalid_batch_layout(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(
        json.dumps(
            {
                "presets": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "description": "Two custom zones",
                        "zones": [
                            {"id": "a", "type": "text", "text_source": "custom", "custom_text": ""},
                            {"id": "b", "type": "text", "text_source": "custom", "custom_text": ""},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PresetConfigError, match="Batch mode requires either exactly one custom text zone or at least one text zone using number, name, caption, title, or subtitle"):
        resolve_batch_preset_mode("bad", config_path=config_path)


def test_build_batch_structured_zones_returns_structured_preset_zones(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")
    zones = build_batch_structured_zones("preset_3", config_path=config_path)
    text_sources = [zone["text_source"] for zone in zones if zone.get("type") == "text"]
    assert text_sources.count("number") == 1
    assert text_sources.count("name") == 1
    assert text_sources.count("caption") == 1


def test_build_batch_structured_zones_rejects_non_structured_preset(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(PresetConfigError, match="Structured batch mode requires a preset with at least one text zone using number, name, caption, title, or subtitle"):
        build_batch_structured_zones("preset_1", config_path=config_path)


def test_build_batch_quote_zones_sets_single_custom_zone(tmp_path: Path):
    config_path = write_config(tmp_path / "batch_quote_presets.json")
    zones = build_batch_quote_zones("preset_1", "Stay steady", config_path=config_path)
    custom_zones = [zone for zone in zones if zone.get("type") == "text" and zone.get("text_source") == "custom"]
    assert len(custom_zones) == 1
    assert custom_zones[0]["custom_text"] == "Stay steady"


def test_build_batch_quote_zones_rejects_zero_custom_text_zones(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(
        json.dumps(
            {
                "presets": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "description": "No custom zones",
                        "zones": [
                            {"id": "a", "type": "text", "text_source": "name", "custom_text": ""},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PresetConfigError, match="exactly one custom text zone"):
        build_batch_quote_zones("bad", "Stay steady", config_path=config_path)


def test_build_batch_quote_zones_rejects_multiple_custom_text_zones(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(
        json.dumps(
            {
                "presets": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "description": "Too many custom zones",
                        "zones": [
                            {"id": "a", "type": "text", "text_source": "custom", "custom_text": ""},
                            {"id": "b", "type": "text", "text_source": "custom", "custom_text": ""},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PresetConfigError, match="exactly one custom text zone"):
        build_batch_quote_zones("bad", "Stay steady", config_path=config_path)


def test_create_update_delete_preset_round_trip(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")
    created = create_preset(
        {
            "id": "preset_new",
            "label": "New Preset",
            "description": "Added in test",
            "zones": [
                {
                    "id": "new-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 30,
                    "text_color": "#FFFFFF",
                    "opacity": 1.0,
                    "x_percent": 50,
                    "y_percent": 50,
                    "alignment": "center",
                    "max_width_percent": 80,
                    "uppercase": False,
                    "bg_shape": "none",
                    "bg_color": "#000000",
                    "bg_opacity": 0.0,
                    "bg_padding": 0,
                    "shadow_enabled": False,
                    "shadow_dx": 0,
                    "shadow_dy": 0,
                    "shadow_blur": 0,
                    "shadow_color": "#000000",
                    "shadow_opacity": 0.0,
                    "outline_enabled": False,
                    "outline_thickness": 0,
                    "outline_color": "#000000",
                }
            ],
        },
        config_path=config_path,
    )
    assert created["id"] == "preset_new"
    assert any(preset["id"] == "preset_new" for preset in list_presets(config_path=config_path))

    updated = update_preset(
        "preset_new",
        {
            "id": "preset_new",
            "label": "Updated Preset",
            "description": "Updated in test",
            "zones": created["zones"],
        },
        config_path=config_path,
        replace=True,
    )
    assert updated["label"] == "Updated Preset"

    deleted = delete_preset("preset_new", config_path=config_path)
    assert deleted["id"] == "preset_new"
    assert all(preset["id"] != "preset_new" for preset in list_presets(config_path=config_path))


def test_create_update_validation_errors(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")

    with pytest.raises(PresetConfigError, match="already exists"):
        create_preset(
            {
                "id": "preset_1",
                "label": "Duplicate",
                "description": "Duplicate id",
                "zones": [
                    {
                        "id": "duplicate",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                    }
                ],
            },
            config_path=config_path,
        )

    with pytest.raises(PresetConfigError, match="non-empty 'label'"):
        create_preset(
            {
                "id": "preset_bad",
                "label": "   ",
                "description": "Has missing label",
                "zones": [
                    {
                        "id": "bad",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                    }
                ],
            },
            config_path=config_path,
        )

    with pytest.raises(PresetConfigError, match="must define at least one zone"):
        create_preset(
            {
                "id": "preset_bad",
                "label": "No zones",
                "description": "No zones",
                "zones": [],
            },
            config_path=config_path,
        )


def test_create_preset_rejects_invalid_numeric_text_zone_value(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")

    with pytest.raises(PresetConfigError, match="font_size"):
        create_preset(
            {
                "id": "preset_bad_numeric",
                "label": "Bad numeric",
                "description": "Invalid font size",
                "zones": [
                    {
                        "id": "bad-text",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                        "font_size": 0,
                    }
                ],
            },
            config_path=config_path,
        )


def test_create_preset_rejects_invalid_typography_field_values(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")

    base_zone = {
        "id": "bad-text",
        "type": "text",
        "text_source": "custom",
        "custom_text": "",
    }
    test_cases = {
        "opacity": 1.2,
        "max_width_percent": 101,
        "bg_opacity": -0.1,
        "bg_padding": -1,
        "shadow_dx": "left",
        "shadow_opacity": -0.5,
        "shadow_blur": -2,
        "outline_thickness": -1,
        "outline_color": "not-a-color",
        "text_color": "#12",
        "outline_enabled": "yes",
        "uppercase": "YES",
    }

    for field, value in test_cases.items():
        preset_id = f"preset_bad_{field}"
        zone = dict(base_zone)
        zone[field] = value

        with pytest.raises(PresetConfigError, match=field.replace("_", " ") if " " in field else field):
            create_preset(
                {
                    "id": preset_id,
                    "label": "Invalid typography",
                    "description": "Invalid typography field",
                    "zones": [zone],
                },
                config_path=config_path,
            )


def test_create_preset_rejects_invalid_typography_boolean_field_types(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")

    with pytest.raises(PresetConfigError, match="shadow_enabled"):
        create_preset(
            {
                "id": "preset_bad_bool_shadow",
                "label": "Invalid bool",
                "description": "Shadow enabled is not bool",
                "zones": [
                    {
                        "id": "bad-text",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                        "shadow_enabled": "on",
                    }
                ],
            },
            config_path=config_path,
        )

    with pytest.raises(PresetConfigError, match="uppercase"):
        create_preset(
            {
                "id": "preset_bad_bool_upper",
                "label": "Invalid bool",
                "description": "Uppercase is not bool",
                "zones": [
                    {
                        "id": "bad-text",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                        "uppercase": 1,
                    }
                ],
            },
            config_path=config_path,
        )

    with pytest.raises(PresetConfigError, match="outline_enabled"):
        create_preset(
            {
                "id": "preset_bad_bool_outline",
                "label": "Invalid bool",
                "description": "Outline enabled is not bool",
                "zones": [
                    {
                        "id": "bad-text",
                        "type": "text",
                        "text_source": "custom",
                        "custom_text": "",
                        "outline_enabled": "true",
                    }
                ],
            },
            config_path=config_path,
        )


def test_create_preset_accepts_valid_typography_field_values(tmp_path: Path):
    config_path = write_config(tmp_path / "presets.json")
    created = create_preset(
        {
            "id": "preset_rich_valid",
            "label": "Rich Typography",
            "description": "Valid typed typography values",
            "zones": [
                {
                    "id": "rich-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 48,
                    "text_color": "#AABBCC",
                    "opacity": 0.85,
                    "x_percent": 42,
                    "y_percent": 60,
                    "alignment": "center",
                    "max_width_percent": 88,
                    "uppercase": True,
                    "bg_shape": "rectangle",
                    "bg_color": "#112233",
                    "bg_opacity": 0.4,
                    "bg_padding": 16,
                    "shadow_enabled": True,
                    "shadow_dx": 4,
                    "shadow_dy": -2,
                    "shadow_blur": 6,
                    "shadow_color": "#334455",
                    "shadow_opacity": 0.7,
                    "outline_enabled": True,
                    "outline_thickness": 5,
                    "outline_color": "#FFEEDD",
                }
            ],
        },
        config_path=config_path,
    )

    assert created["id"] == "preset_rich_valid"
    presets = list_presets(config_path)
    assert any(preset["id"] == "preset_rich_valid" for preset in presets)
