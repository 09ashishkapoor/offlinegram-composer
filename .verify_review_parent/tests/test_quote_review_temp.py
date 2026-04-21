import json
from pathlib import Path

import pytest

from presets import PresetConfigError, build_batch_quote_zones
from processor import ProcessorError, parse_quote_lines


def test_parse_quote_lines_ignores_blank_lines():
    entries = parse_quote_lines("First quote\n\nSecond quote\n  \nThird quote\n")
    assert entries == ["First quote", "Second quote", "Third quote"]


def test_parse_quote_lines_rejects_empty_input():
    with pytest.raises(ProcessorError, match="does not contain any usable quotes"):
        parse_quote_lines("\n   \n")


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
