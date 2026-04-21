import json
from pathlib import Path

import pytest

from presets import PresetConfigError, build_batch_quote_zones, build_preset_zones, list_presets


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


def test_list_presets_returns_two_launch_presets(tmp_path: Path):
    config_path = tmp_path / "presets.json"
    config_path.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")
    presets = list_presets(config_path)
    assert [preset["id"] for preset in presets] == ["preset_1", "preset_2"]


def test_build_batch_quote_zones_sets_single_custom_zone():
    zones = build_batch_quote_zones("preset_1", "Stay steady")
    custom_zones = [zone for zone in zones if zone.get("type") == "text" and zone.get("text_source") == "custom"]
    assert len(custom_zones) == 1
    assert custom_zones[0]["custom_text"] == "Stay steady"


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
