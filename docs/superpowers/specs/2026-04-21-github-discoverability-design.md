# GitHub Discoverability Design

## Goal

Improve discoverability for general users who land on the GitHub repository page by making the repo describe the tool in user-facing terms instead of implementation-first terms.

This work is limited to GitHub-facing surfaces: repository topics, short repository description guidance, and the README content that is visible on the repo landing page.

## Scope

### In scope

- Replace mismatched GitHub topics with topics that better reflect the actual product
- Tighten the recommended repository description to describe the tool in plain user language
- Rewrite the top section of `README.md` so the first screenful immediately explains what the tool does, who it is for, and why it is useful
- Keep the existing screenshots, setup flow, and feature detail, but reorder and reframe them where necessary for clarity

### Out of scope

- GitHub Pages SEO or search-engine optimization outside GitHub
- Application UI changes
- New product features
- Packaging or distribution changes
- Social media marketing copy outside the repository page

## Current Problems

### Topic mismatch

The current topic set:

- `instagram`
- `offline-first`
- `python`
- `carousel`
- `overlay`

does not reflect how a general user would search for this project.

Problems with the current set:

- `offline-first` suggests sync-capable application architecture rather than a fully local tool
- `carousel` implies multi-slide post authoring, which is not the primary behavior of the app
- `overlay` is too generic to help discovery
- `python` is implementation metadata, not user-intent metadata
- only `instagram` clearly points at the user-facing use case

### README positioning

The current README explains the stack and behavior accurately, but the opening framing is too narrow and somewhat technical:

- it leads with "locally-hosted web app"
- it under-emphasizes quote-image generation and offline creator workflow
- it assumes the reader already understands why they want this tool

For a general user browsing GitHub, the repo needs to read as a practical creator tool first.

## Positioning Strategy

### Primary audience

General users who want a simple offline tool for making quote images and square social posts.

### Product framing

The repository should position the app as:

`An offline tool for creating quote images and square social media posts in the browser.`

This is better than stack-led framing because it emphasizes:

- the output users care about
- the offline privacy advantage
- the browser-based ease of use

### Messaging priorities

The first repo screen should answer these questions in order:

1. What is this?
2. What can I make with it?
3. Why would I use this instead of another tool?
4. How do I try it quickly?

Implementation details like FastAPI, Skia, and Python should remain in the README, but lower on the page.

## Recommended Topic Set

Replace the current topics with this GitHub topic set:

- `instagram`
- `social-media`
- `social-media-tool`
- `quote-generator`
- `quote-to-image`
- `quote-image`
- `offline-app`
- `content-creation`

## Topic Rationale

### Keep

- `instagram`
  - still relevant because the app is explicitly built around square post composition and Instagram-style output

### Add

- `social-media`
  - broad but highly active and closer to how users classify the problem space
- `social-media-tool`
  - better expresses that this repository is a usable tool rather than a tutorial or integration
- `quote-generator`
  - aligns with active GitHub topic usage around quote-making workflows
- `quote-to-image`
  - directly describes one of the core user outcomes
- `quote-image`
  - captures an adjacent phrase used by similar image-quote tools
- `offline-app`
  - more accurate than `offline-first` for this repository's actual behavior
- `content-creation`
  - places the repo in a broader creator-tool ecosystem without becoming purely technical

### Remove

- `offline-first`
- `python`
- `carousel`
- `overlay`

These removed topics either misdescribe the product or optimize for the wrong audience.

## Repository Description Guidance

Recommended repository description:

`Create offline quote images and square social media posts in your browser.`

This description is preferred because it:

- starts with the user outcome
- keeps the offline differentiator
- avoids unnecessary implementation wording
- stays readable in GitHub search results and repository cards

## README Changes

### Opening section

Rewrite the README opening so it leads with the creator use case:

- offline quote images
- square social media posts
- browser-based workflow
- no accounts, no cloud, no telemetry

The first paragraph should avoid leading with "locally-hosted web app" and instead describe the tool as something a creator can use immediately.

### Hero structure

Recommended top-of-README order:

1. project name
2. one-sentence value proposition
3. project site link
4. primary screenshot
5. short "Why use it" or "What you can do" section
6. quick start

### Feature language

Feature bullets should be rewritten in plain-language user terms where needed:

- "make quote images from local files"
- "create square social posts offline"
- "batch-create multiple images from a text file"
- "pick a preset and export PNGs"

The underlying technical truth stays the same, but the phrasing should bias toward user outcomes.

### Technical details

Keep the existing stack and test sections in the README, but below the user-facing sections.

This preserves contributor usefulness without letting the repo read like a developer-only project.

## Acceptance Criteria

- The repository has a user-intent topic set rather than a stack-led topic set
- The recommended short description reads naturally to a non-technical GitHub visitor
- The first screenful of the README explains the tool in user language
- The README still preserves setup instructions, screenshots, feature detail, and technical reference material
- The repository page reads like a creator tool first and a Python codebase second
