# Offlinegram Composer Phase 2–3 Tracker

Tracks the remaining roadmap work after Phase 1.

- Source of truth: [`docs/ROADMAP.md`](./ROADMAP.md)
- Last reviewed: 2026-04-24

## Status legend

- `[x]` done
- `[-]` partial
- `[ ]` pending

---

## Phase 2 — Make presets and exports first-class

### Features

- [x] Add a preset editor UI to create, duplicate, rename, delete, and save presets without hand-editing `presets.json`.
- [x] Allow users to save **Customize overlay** changes back into reusable presets.
- [-] Add richer typography controls in the UI using the existing fonts support.
  - Done: font picker, stroke/outline, shadow, and background controls.
  - Remaining: spacing and line-height controls.
- [-] Add export profiles for PNG/JPG/WebP, quality/size options, and predictable filename templates such as `{index}`, `{source}`, `{name}`, or `{slug}`.
  - Done: format selection, quality controls, and filename templates.
  - Remaining: reusable export profiles and size options.
- [-] Expand import formats beyond line-based text to CSV/TSV/JSON with field mapping for structured presets.
  - Done: CSV/TSV import inspection and field mapping.
  - Remaining: JSON import support.
- [ ] Add an output history/recent exports view for quick reuse and re-export.

### Testing

- [x] Add preset round-trip tests for create/update/delete and validation failures.
- [-] Add API tests for export profile validation and filename template handling.
  - Done: export format, quality, and filename-template validation coverage.
  - Remaining: tests for reusable export profiles and size options.
- [-] Add parser tests for CSV/JSON field mapping and malformed records.
  - Done: CSV/TSV field mapping and malformed-record coverage.
  - Remaining: JSON parser coverage.
- [x] Add frontend regression coverage for preset editing, font selection, and export option flows.

### Phase 2 priority checklist

1. Add spacing and line-height controls.
2. Add reusable export profiles and size options.
3. Add JSON structured import support.
4. Add output history / recent exports UI.
5. Fill in remaining API/parser tests for the unfinished items above.

---

## Phase 3 — Package and polish for real-world batch use

### Features

- [x] Improve cross-platform file and folder picking so the app works more smoothly outside the current Windows-first native picker path.
- [ ] Add batch progress, cancel, retry, and per-item failure reporting for larger jobs.
- [ ] Add startup diagnostics for missing fonts, missing dependencies, and renderer/runtime issues.
- [-] Improve performance on repeated preview/export operations and larger folders.
  - Done: some render optimizations already exist, including font caching and clamped preview sampling.
  - Remaining: broader large-batch and repeated-export performance work.
- [ ] Package the app into an easier install/run experience beyond the current setup and launch scripts.

### Testing

- [-] Add larger-batch stress tests and timeout/error-path coverage.
  - Done: some error-path coverage already exists for batch and picker flows.
  - Remaining: stress and timeout-focused batch coverage.
- [ ] Add clean-machine install/launch smoke tests.
- [ ] Add basic performance baselines for preview and batch export.
- [-] Add manual QA checklist coverage for batch cancel/retry and cross-platform picker fallbacks.
  - Done: picker fallback behavior has some automated coverage.
  - Remaining: manual QA checklist coverage and any cancel/retry coverage.

### Phase 3 priority checklist

1. Add batch progress, cancel, retry, and per-item failure reporting.
2. Add startup diagnostics.
3. Define a packaging/distribution path beyond the current scripts.
4. Add larger-batch stress coverage and performance baselines.
5. Write the manual QA checklist for picker fallbacks and future cancel/retry behavior.

---

## Suggested next milestones

### Next Phase 2 milestone

- Typography completion: spacing + line-height
- Export profiles + size options
- JSON structured import support

### Next Phase 3 milestone

- Batch job progress / cancel / retry / per-item failure reporting
- Stress tests for larger batch runs
