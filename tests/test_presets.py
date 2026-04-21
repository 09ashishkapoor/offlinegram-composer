import json
from pathlib import Path

import pytest

from presets import (
    PresetConfigError,
    build_batch_quote_zones,
    build_batch_structured_zones,
    build_preset_zones,
    list_presets,
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
