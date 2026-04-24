import os
import json
import re
import time
from pathlib import Path

from PIL import Image
import pytest
from playwright.sync_api import Page, expect


def _write_image(path: Path, color: tuple[int, int, int, int] = (25, 36, 52, 255)) -> Path:
    Image.new("RGBA", (800, 800), color).save(path)
    return path


def _wait_for_predicate(predicate, timeout_sec: float = 2.0, interval_sec: float = 0.05) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval_sec)
    raise TimeoutError("Timed out waiting for predicate in test")


@pytest.mark.e2e
def test_frontend_boot_smoke(app_url: str, page: Page):
    errors: list[str] = []

    def record_error(message: str) -> None:
        errors.append(message)

    page.on("pageerror", lambda exc: record_error(f"pageerror: {exc}"))
    page.on(
        "console",
        lambda msg: record_error(f"{msg.type}: {msg.text}")
        if msg.type in {"error", "warning"}
        else None,
    )

    page.goto(f"{app_url}/", wait_until="networkidle")

    expect(page.locator("#spc-drop-zone")).to_be_visible()
    expect(page.locator("#spc-text")).to_be_visible()
    expect(page.locator("#preset-options")).to_be_visible()
    expect(page.locator("#spc-preview")).to_be_visible()
    expect(page.locator("#spc-export")).to_be_visible()
    expect(page.locator("#batch-preview")).to_be_visible()
    expect(page.locator("#batch-export")).to_be_visible()
    expect(page.locator("#batch-meta")).to_be_visible()
    expect(page.locator("#batch-image-dir")).to_be_visible()
    expect(page.locator("#batch-quotes-file")).to_be_visible()

    # Ensure core presets render (at least one available card).
    page.wait_for_selector("#preset-options .preset-card", state="visible", timeout=5000)
    assert page.locator("#preset-options .preset-card").count() > 0

    assert not any("error" in entry.lower() for entry in errors), f"Browser JS/console errors: {errors}"


@pytest.mark.e2e
def test_frontend_single_image_preview_and_export_smoke(tmp_path: Path, app_url: str, page: Page):
    source_image = _write_image(tmp_path / "source.png")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    page.goto(f"{app_url}/", wait_until="networkidle")

    # Configure output folder through existing session state helper (no OS picker required).
    page.evaluate(
        "([outputDir]) => { window.applySessionState({ outputDir }); window.updatePathPills(); }",
        [str(output_dir.resolve())],
    )
    page.set_input_files("#spc-image-upload", str(source_image))
    page.fill("#spc-text", "Smoke test text")

    # Pick the first available preset explicitly so the request can always resolve.
    page.locator("#preset-options .preset-card[data-preset-id='preset_1']").click()

    page.click("#spc-preview")
    expect(page.locator("#spc-preview-image")).to_be_visible()
    expect(page.locator("#preview-meta")).to_contain_text("Preview ready.")

    page.click("#spc-export")
    expect(page.locator("#preview-meta")).to_contain_text("Saved to")

    _wait_for_predicate(lambda: any(file.suffix.lower() == ".png" for file in output_dir.iterdir()))
    png_outputs = list(output_dir.glob("*.png"))
    assert len(png_outputs) == 1
    assert os.path.exists(png_outputs[0])


@pytest.mark.e2e
def test_frontend_session_state_persists_across_reload(tmp_path: Path, app_url: str, page: Page):
    image_file = _write_image(tmp_path / "image-source.png")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    batch_images = tmp_path / "batch-images"
    batch_images.mkdir()
    batch_quotes_file = tmp_path / "quotes.txt"
    batch_quotes_file.write_text("Reload quote\n", encoding="utf-8")
    batch_output = tmp_path / "batch-output"
    batch_output.mkdir()

    page.goto(f"{app_url}/", wait_until="networkidle")
    page.fill("#spc-text", "Quote from session")

    # Seed session state for both single and batch workflows.
    page.evaluate(
        "([presetId, text, imagePath, outputDir, batchImageDir, batchQuotesPath, batchOutputDir]) => {\n"
        "  window.applySessionState({\n"
        "    activePresetId: presetId,\n"
        "    imagePath,\n"
        "    outputDir,\n"
        "    batchImageDir,\n"
        "    batchQuotesPath,\n"
        "    batchOutputDir,\n"
        "    exportFormat: 'webp',\n"
        "    exportQuality: '83',\n"
        "    filenameTemplate: '{index}_{preset}_{base_name}',\n"
        "    batchExportFormat: 'jpg',\n"
        "    batchExportQuality: '67',\n"
        "    batchFilenameTemplate: '{index}_{source_name}_{preset}',\n"
        "    text,\n"
        "  });\n"
        "  window.persistSessionState();\n"
        "}",
        [
            "preset_2",
            "Quote from session",
            str(image_file),
            str(output_dir),
            str(batch_images),
            str(batch_quotes_file),
            str(batch_output),
        ],
    )

    page.reload(wait_until="networkidle")

    page.wait_for_selector("#preset-options .preset-card", state="visible", timeout=5000)

    # Verify single-image state restored.
    expect(page.locator("#spc-text")).to_have_value("Quote from session")
    expect(page.locator("#spc-image-source")).to_contain_text(str(image_file))
    expect(page.locator("#spc-output-path")).to_contain_text(str(output_dir))
    expect(page.locator("#spc-export-format")).to_have_value("webp")
    expect(page.locator("#spc-export-quality")).to_have_value("83")
    expect(page.locator("#spc-export-filename-template")).to_have_value("{index}_{preset}_{base_name}")
    expect(page.locator("#preset-options .preset-card[data-preset-id='preset_2']")).to_have_class(re.compile(r"\bactive\b"))

    # Verify batch state restored.
    expect(page.locator("#batch-image-dir")).to_contain_text(str(batch_images))
    expect(page.locator("#batch-quotes-file")).to_contain_text(str(batch_quotes_file))
    expect(page.locator("#batch-output-dir")).to_contain_text(str(batch_output))
    expect(page.locator("#batch-export-format")).to_have_value("jpg")
    expect(page.locator("#batch-export-quality")).to_have_value("67")
    expect(page.locator("#batch-export-filename-template")).to_have_value("{index}_{source_name}_{preset}")


@pytest.mark.e2e
def test_frontend_batch_preview_mismatch_shows_error(tmp_path: Path, app_url: str, page: Page):
    image_dir = tmp_path / "batch_images"
    image_dir.mkdir()
    _write_image(image_dir / "a.png", (14, 22, 32, 255))
    _write_image(image_dir / "b.png", (16, 24, 36, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("Only one quote\n", encoding="utf-8")

    page.goto(f"{app_url}/", wait_until="networkidle")
    page.set_input_files("#batch-quotes-upload", str(text_file))

    # Seed batch image folder through existing session state helper (no OS picker required).
    page.evaluate(
        "([imageDir]) => { window.applySessionState({ batchImageDir: imageDir }); window.updateBatchPathPills(); }",
        [str(image_dir.resolve())],
    )

    page.locator("#preset-options .preset-card[data-preset-id='preset_1']").click()

    page.click("#batch-preview")
    expect(page.locator("#batch-meta")).to_contain_text(
        "Batch mode expects one quote per image, but counts differ: found 2 images and 1 quotes.",
        timeout=5000,
    )
    expect(page.locator("#batch-meta")).to_contain_text(
        "Ensure every image has exactly one quote and retry.",
        timeout=5000,
    )


@pytest.mark.e2e
def test_frontend_batch_csv_mapping_preview_flow(tmp_path: Path, app_url: str, page: Page):
    image_dir = tmp_path / "batch_images"
    image_dir.mkdir()
    _write_image(image_dir / "a.png", (20, 30, 40, 255))
    _write_image(image_dir / "b.png", (40, 50, 60, 255))

    csv_file = tmp_path / "entries.csv"
    csv_file.write_text("No,Name,Caption\n1,Name A,Caption A\n2,Name B,Caption B\n", encoding="utf-8")

    page.goto(f"{app_url}/", wait_until="networkidle")

    page.evaluate(
        "window.__capturedInspectRequests = [];"
        "window.__capturedBatchPreviewRequests = [];"
        "const originalFetch = window.fetch.bind(window);"
        "window.fetch = async (input, init = {}) => {"
        "  const url = typeof input === 'string' ? input : (input?.url || '');"
        "  const payload = {};"
        "  if (url && String(url).includes('/api/batch/import/inspect')) {"
        "    const body = init.body;"
        "    if (body instanceof FormData) {"
        "      for (const [key, value] of body.entries()) {"
        "        if (value instanceof File) {"
        "          payload[key] = `FILE:${value.name}`;"
        "        } else {"
        "          payload[key] = String(value);"
        "        }"
        "      }"
        "    }"
        "    window.__capturedInspectRequests.push(payload);"
        "  }"
        "  if (url && String(url).includes('/api/batch/quotes/preview')) {"
        "    const body = init.body;"
        "    if (body instanceof FormData) {"
        "      for (const [key, value] of body.entries()) {"
        "        if (value instanceof File) {"
        "          payload[key] = `FILE:${value.name}`;"
        "        } else {"
        "          payload[key] = String(value);"
        "        }"
        "      }"
        "    }"
        "    window.__capturedBatchPreviewRequests.push(payload);"
        "  }"
        "  return originalFetch(input, init);"
        "};"
    )

    page.set_input_files("#batch-quotes-upload", str(csv_file))

    page.evaluate(
        "([imageDir]) => { window.applySessionState({ batchImageDir: imageDir }); window.updateBatchPathPills(); }",
        [str(image_dir.resolve())],
    )

    page.locator("#preset-options .preset-card[data-preset-id='preset_3']").click()

    # Mapping panel should appear automatically for CSV structured input.
    expect(page.locator("#batch-structured-mapping")).to_be_visible()
    expect(page.locator("#batch-field-number")).to_be_visible()
    expect(page.locator("#batch-field-name")).to_be_visible()
    expect(page.locator("#batch-field-caption")).to_be_visible()

    page.click("#batch-preview")
    expect(page.locator("#batch-meta")).to_contain_text("Showing 2 sample preview", timeout=8000)

    inspect_payload = page.evaluate("window.__capturedInspectRequests[0] || {}")
    assert inspect_payload.get("import_format") == "csv"
    assert inspect_payload.get("preset_id") == "preset_3"

    preview_payload = page.evaluate("window.__capturedBatchPreviewRequests[0] || {}")
    assert preview_payload.get("import_format") == "csv"
    assert preview_payload.get("preset_id") == "preset_3"

    mapping_payload = json.loads(preview_payload.get("field_mapping_json", "{}"))
    assert mapping_payload.get("number") == "No"
    assert mapping_payload.get("name") == "Name"
    assert mapping_payload.get("caption") == "Caption"

    # Ensure selects reflect detected mapping.
    expect(page.locator("#batch-field-number")).to_have_value("No")
    expect(page.locator("#batch-field-name")).to_have_value("Name")
    expect(page.locator("#batch-field-caption")).to_be_visible()
    expect(page.locator("#batch-field-caption")).to_have_value("Caption")


@pytest.mark.e2e
def test_frontend_export_options_flow_and_filename_template(tmp_path: Path, app_url: str, page: Page):
    source_image = _write_image(tmp_path / "source.png")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    page.goto(f"{app_url}/", wait_until="networkidle")

    page.evaluate(
        "window.__capturedGenerateRequests = [];"
        " const originalFetch = window.fetch.bind(window);"
        " window.fetch = async (input, init = {}) => {"
        "   const url = typeof input === 'string' ? input : (input?.url || '');"
        "   if (url && String(url).includes('/api/generate')) {"
        "     const body = init.body;"
        "     const payload = {};"
        "     if (body instanceof FormData) {"
        "       for (const [key, value] of body.entries()) {"
        "         if (value instanceof File) {"
        "           payload[key] = `FILE:${value.name}`;"
        "         } else {"
        "           payload[key] = String(value);"
        "         }"
        "       }"
        "     }"
        "     window.__capturedGenerateRequests.push(payload);"
        "   }"
        "   return originalFetch(input, init);"
        " };"
        " window.updateExportOptionsFromInputs && window.updateExportOptionsFromInputs();",
    )
    page.evaluate(
        "([outputDir]) => { window.applySessionState({ outputDir }); window.updatePathPills(); }",
        [str(output_dir.resolve())],
    )

    page.set_input_files("#spc-image-upload", str(source_image))
    page.fill("#spc-text", "Export option smoke")
    page.locator("#preset-options .preset-card[data-preset-id='preset_1']").click()

    expect(page.locator("text=Deterministic naming supports")).to_be_visible()

    page.select_option("#spc-export-format", "jpg")
    page.fill("#spc-export-quality", "73")
    page.fill("#spc-export-filename-template", "{index}_{preset}_{source_name}")

    page.click("#spc-export")
    expect(page.locator("#preview-meta")).to_contain_text("Saved to", timeout=10000)

    first_payload = page.evaluate("window.__capturedGenerateRequests[0] || {}")
    assert first_payload.get("export_format") == "jpg"
    assert first_payload.get("export_quality") == "73"
    assert first_payload.get("filename_template") == "{index}_{preset}_{source_name}"

    page.select_option("#spc-export-format", "png")
    page.fill("#spc-export-quality", "62")
    page.fill("#spc-export-filename-template", "{index}_{preset}_{source_name}")

    page.click("#spc-export")
    expect(page.locator("#preview-meta")).to_contain_text("Saved to", timeout=10000)
    second_payload = page.evaluate("window.__capturedGenerateRequests[1] || {}")
    assert second_payload.get("export_format") == "png"
    assert "export_quality" not in second_payload
    assert second_payload.get("filename_template") == "{index}_{preset}_{source_name}"


@pytest.mark.e2e
def test_frontend_advanced_overlay_controls_apply_to_overlay_json(tmp_path: Path, app_url: str, page: Page):
    source_image = _write_image(tmp_path / "source.png")

    page.goto(f"{app_url}/", wait_until="networkidle")

    page.evaluate(
        "window.__capturedPreviewRequests = [];"
        " const originalFetch = window.fetch.bind(window);"
        " window.fetch = async (input, init = {}) => {"
        "   const url = typeof input === 'string' ? input : (input?.url || '');"
        "   if (url && String(url).includes('/api/preview')) {"
        "     const body = init.body;"
        "     const payload = {};"
        "     if (body instanceof FormData) {"
        "       for (const [key, value] of body.entries()) {"
        "         payload[key] = value instanceof File ? `FILE:${value.name}` : String(value);"
        "       }"
        "     }"
        "     window.__capturedPreviewRequests.push(payload);"
        "   }"
        "   return originalFetch(input, init);"
        " };"
    )

    page.set_input_files("#spc-image-upload", str(source_image))
    page.fill("#spc-text", "Overlay JSON smoke")
    page.locator("#preset-options .preset-card[data-preset-id='preset_1']").click()

    page.locator("#advanced-toggle").click()
    expect(page.locator("#advanced-font-name")).to_be_visible()
    expect(page.locator("#advanced-font-size")).to_be_visible()
    expect(page.locator("#advanced-outline-thickness")).to_be_visible()
    expect(page.locator("#advanced-shadow-opacity")).to_be_visible()

    font_choice = None
    if page.locator("#advanced-font-name option").count() > 1:
        font_choice = page.locator("#advanced-font-name option").nth(1).get_attribute("value")
    else:
        font_choice = page.locator("#advanced-font-name option").first.get_attribute("value")

    assert font_choice is not None
    page.select_option("#advanced-font-name", value=font_choice)

    page.fill("#advanced-font-size", "88")
    page.fill("#advanced-x-percent", "33")
    page.fill("#advanced-y-percent", "62")
    page.select_option("#advanced-alignment", "right")
    page.fill("#advanced-max-width-percent", "90")
    page.fill("#advanced-opacity", "0.84")
    page.check("#advanced-uppercase")
    page.fill("#advanced-text-color", "#123456")
    page.select_option("#advanced-bg-shape", "rounded_rectangle")
    page.fill("#advanced-bg-color", "#ff8800")
    page.fill("#advanced-bg-opacity", "0.42")
    page.fill("#advanced-bg-padding", "18")
    page.uncheck("#advanced-shadow-enabled")
    page.fill("#advanced-shadow-dx", "3")
    page.fill("#advanced-shadow-dy", "6")
    page.fill("#advanced-shadow-blur", "10")
    page.fill("#advanced-shadow-color", "#00ff88")
    page.fill("#advanced-shadow-opacity", "0.77")
    page.check("#advanced-outline-enabled")
    page.fill("#advanced-outline-thickness", "7")
    page.fill("#advanced-outline-color", "#4455ff")

    page.click("#spc-preview")
    expect(page.locator("#spc-preview-image")).to_be_visible()

    payload = page.evaluate("window.__capturedPreviewRequests[0] || {}")
    overlay_json = payload.get("overlay_json")
    assert overlay_json, "Expected overlay_json to be included in preview request"
    overlay_data = json.loads(overlay_json)
    assert isinstance(overlay_data, list)
    assert overlay_data

    first_zone = next((zone for zone in overlay_data if zone.get("type") == "text"), None)
    assert first_zone is not None
    assert first_zone["font_name"] == font_choice
    assert float(first_zone["font_size"]) == 88.0
    assert float(first_zone["x_percent"]) == 33.0
    assert float(first_zone["y_percent"]) == 62.0
    assert first_zone["alignment"] == "right"
    assert float(first_zone["max_width_percent"]) == 90.0
    assert float(first_zone["opacity"]) == 0.84
    assert first_zone["uppercase"] is True
    assert first_zone["bg_shape"] == "rounded_rectangle"
    assert float(first_zone["bg_opacity"]) == 0.42
    assert float(first_zone["bg_padding"]) == 18.0
    assert first_zone["shadow_enabled"] is False
    assert float(first_zone["shadow_dx"]) == 3.0
    assert float(first_zone["shadow_dy"]) == 6.0
    assert float(first_zone["shadow_blur"]) == 10.0
    assert first_zone["shadow_color"] == "#00ff88"
    assert float(first_zone["shadow_opacity"]) == 0.77
    assert first_zone["outline_enabled"] is True
    assert float(first_zone["outline_thickness"]) == 7.0
    assert first_zone["outline_color"] == "#4455ff"
    assert first_zone["text_color"] == "#123456"
    assert first_zone["bg_color"] == "#ff8800"


@pytest.mark.e2e
def test_frontend_preset_duplication_and_persistence(tmp_path: Path, app_url: str, page: Page):
    duplicated_label = "Preset 1 persisted"
    duplicated_description = "Preset persistence smoke"
    presets_path = Path(os.environ["OFFLINEGRAM_TEST_PRESETS_PATH"])
    original_presets = presets_path.read_text(encoding="utf-8")

    try:
        page.goto(f"{app_url}/", wait_until="networkidle")

        page.wait_for_selector("#preset-options .preset-card", state="visible", timeout=5000)
        first_card = page.locator("#preset-options .preset-card").first
        initial_preset_label = first_card.locator("strong").text_content() or "Preset 1"
        first_card.click()

        # Duplicate the current preset and then modify visible metadata.
        page.click("#spc-preset-duplicate")
        page.wait_for_timeout(400)
        expect(page.locator("#spc-preset-label")).to_have_value(re.compile(r"copy", re.IGNORECASE))

        page.fill("#spc-preset-label", duplicated_label)
        page.fill("#spc-preset-description", duplicated_description)
        page.click("#spc-preset-save-metadata")

        # Persisted card should now be visible in same session.
        expect(page.locator(f".preset-card:has-text(\"{duplicated_label}\")")).to_be_visible()

        # Ensure page reload picks the same preset back from API + session state.
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#preset-options .preset-card", state="visible", timeout=5000)

        # Duplicate card should still exist and be editable after reload.
        expect(page.locator(f".preset-card:has-text(\"{duplicated_label}\")")).to_be_visible()
        expect(page.locator("#spc-preset-label")).to_have_value(duplicated_label)
        expect(page.locator("#spc-preset-description")).to_have_value(duplicated_description)

        # Cleanup: remove the duplicated preset to avoid impacting follow-up tests.
        page.locator(f".preset-card:has-text(\"{duplicated_label}\")").click()
        page.click("#spc-preset-delete")

        expect(page.locator(f".preset-card:has-text(\"{duplicated_label}\")")).to_have_count(0)
        expect(page.locator("#spc-preset-label")).to_have_value(initial_preset_label)
    finally:
        presets_path.write_text(original_presets, encoding="utf-8")
