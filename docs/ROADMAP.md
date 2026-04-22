# Offlinegram Composer Roadmap

## Product direction

This app already delivers the core local-first workflow:
- compose text overlays on images
- preview and export single images
- run preset-driven batch generation
- support structured text inputs for multi-field layouts

The next roadmap should focus on three things in order:
1. **stabilize the current workflow**
2. **make presets and exports more reusable**
3. **improve packaging and larger-batch usability**

---

## Phase 1 — Stabilize the shipped core

### Goal
Make the existing single-image and structured batch flows more reliable, easier to understand, and safer to extend.

### Priority
**Highest**

### Features
- Improve preflight validation and error messaging for image/text count mismatches, missing presets, invalid structured lines, and unreadable paths.
- Surface better preset-mode guidance in the UI so users know whether a preset expects a single quote or structured fields.
- Persist lightweight session state in the frontend for last-used preset, paths, and recent inputs.
- Refactor overlapping validation/request handling in `app.py` and reduce fragile branching in `static/js/app.js`.
- Clarify the role of legacy generic batch endpoints versus the newer preset-aware quote/structured batch flow.

### Testing
- Expand API coverage for invalid structured text, malformed uploads, bad file paths, missing presets, and encoding issues.
- Add more parser edge-case tests in `tests/test_processor.py`.
- Add render smoke/golden tests for the shipped presets in `presets.json`.
- Add a lightweight frontend smoke test path for load → preview → export and batch preview error handling.

### Why now
The app already has meaningful capability. The biggest short-term value is reducing friction and regression risk before adding broader surface area.

---

## Phase 2 — Make presets and exports first-class

### Goal
Turn the current config-driven workflow into a more reusable, user-facing system.

### Priority
**High**

### Features
- Add a preset editor UI to create, duplicate, rename, delete, and save presets without hand-editing `presets.json`.
- Allow users to save "Customize overlay" changes back into reusable presets.
- Add richer typography controls in the UI using the existing fonts support: font picker, spacing, line-height, stroke, shadow, and background controls.
- Add export profiles for PNG/JPG/WebP, quality/size options, and predictable filename templates such as `{index}`, `{source}`, `{name}`, or `{slug}`.
- Expand import formats beyond line-based text to CSV/TSV/JSON with field mapping for structured presets.
- Add an output history/recent exports view for quick reuse and re-export.

### Testing
- Add preset round-trip tests for create/update/delete and validation failures.
- Add API tests for export profile validation and filename template handling.
- Add parser tests for CSV/JSON field mapping and malformed records.
- Add frontend regression coverage for preset editing, font selection, and export option flows.

### Why now
Presets are already the product's strongest abstraction. Making them editable and reusable will create the biggest usability jump after core stabilization.

---

## Phase 3 — Package and polish for real-world batch use

### Goal
Make the app easier to distribute and more dependable for larger export jobs.

### Priority
**Medium**

### Features
- Improve cross-platform file and folder picking so the app works more smoothly outside the current Windows-first native picker path.
- Add batch progress, cancel, retry, and per-item failure reporting for larger jobs.
- Add startup diagnostics for missing fonts, missing dependencies, and renderer/runtime issues.
- Improve performance on repeated preview/export operations and larger folders.
- Package the app into an easier install/run experience beyond the current setup and launch scripts.

### Testing
- Add larger-batch stress tests and timeout/error-path coverage.
- Add clean-machine install/launch smoke tests.
- Add basic performance baselines for preview and batch export.
- Add manual QA checklist coverage for batch cancel/retry and cross-platform picker fallbacks.

### Why later
Packaging and long-run batch polish are most valuable once the core workflow and preset model are stable enough to ship with confidence.

---

## Suggested implementation order

1. **Phase 1:** harden the existing compose and structured batch flow
2. **Phase 2:** add preset management, richer exports, and stronger import flexibility
3. **Phase 3:** package the app and improve long-running batch operations

---

## Testing roadmap summary

Testing should grow with the product, not after it.

### Immediate
- Expand backend API and parser edge-case coverage.
- Add preset render smoke/golden tests.
- Add minimal frontend smoke coverage for the main happy paths.

### Next
- Add regression coverage for preset editing and export configuration.
- Add structured import format tests for CSV/JSON workflows.

### Later
- Add install/launch smoke checks, batch stress coverage, and simple performance baselines.

---

## Recommended next milestone

If only one milestone is tackled next, it should be:

**Phase 1: stabilize the existing compose + structured batch workflow, while adding missing test coverage around error handling and preset rendering.**
