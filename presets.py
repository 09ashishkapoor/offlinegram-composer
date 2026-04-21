from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PRESETS_CONFIG_PATH = BASE_DIR / "presets.json"


class PresetConfigError(ValueError):
    pass


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PresetConfigError("Preset config file was not found.") from exc
    except json.JSONDecodeError as exc:
        raise PresetConfigError("Preset config file is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise PresetConfigError("Preset config root must be an object.")
    return payload


def _validate_preset(preset: dict[str, Any]) -> dict[str, Any]:
    required_fields = ("id", "label", "description", "zones")
    for field in required_fields:
        if field not in preset:
            raise PresetConfigError(f"Preset is missing required field '{field}'.")

    zones = preset["zones"]
    if not isinstance(zones, list) or not zones:
        raise PresetConfigError(f"Preset '{preset['id']}' must define at least one zone.")

    for index, zone in enumerate(zones):
        if not isinstance(zone, dict):
            raise PresetConfigError(f"Preset '{preset['id']}' zone #{index + 1} must be an object.")

    return preset


def load_preset_catalog(config_path: Path = PRESETS_CONFIG_PATH) -> list[dict[str, Any]]:
    payload = _load_raw_config(config_path)
    presets = payload.get("presets")
    if not isinstance(presets, list) or not presets:
        raise PresetConfigError("Preset config must define a non-empty 'presets' list.")
    return [_validate_preset(dict(preset)) for preset in presets]


def list_presets(config_path: Path = PRESETS_CONFIG_PATH) -> list[dict[str, str]]:
    return [
        {
            "id": preset["id"],
            "label": preset["label"],
            "description": preset["description"],
        }
        for preset in load_preset_catalog(config_path)
    ]


def _get_preset_zones(preset_id: str, config_path: Path) -> list[dict[str, Any]]:
    for preset in load_preset_catalog(config_path):
        if preset["id"] == preset_id:
            return [dict(zone) for zone in preset["zones"]]
    raise PresetConfigError(f"Unknown preset '{preset_id}'.")


def build_preset_zones(
    preset_id: str,
    text: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[dict[str, Any]]:
    zones = _get_preset_zones(preset_id, config_path)
    for zone in zones:
        if zone.get("type") == "text" and zone.get("text_source") == "custom":
            zone["custom_text"] = text
    return zones


def build_batch_quote_zones(
    preset_id: str,
    quote: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[dict[str, Any]]:
    zones = _get_preset_zones(preset_id, config_path)
    custom_text_zones = [
        zone for zone in zones if zone.get("type") == "text" and zone.get("text_source") == "custom"
    ]
    if len(custom_text_zones) != 1:
        raise PresetConfigError("Batch mode requires a preset with exactly one custom text zone.")

    custom_text_zones[0]["custom_text"] = quote
    return zones
