---
name: ui-inspection
description: "Design or inspect website and game interfaces against screenshots and interaction evidence."
---

# Ui Inspection

Assigned roles: UI / visual QA.

## Tools and readiness

Proposed browser automation via Playwright and screenshot-capable vision adapter; not wired into current runtime.

These instructions do not install tools or grant tool access. If required evidence cannot be
obtained with the connected adapter, mark it missing and return a bounded plan or blocker.

## Workflow

Record target URL/build, viewport and interaction path. Capture baseline and candidate views, console errors and behavior checks; inspect real pixels with an image-capable model. Compare layout, readability, keyboard navigation and responsive behavior against acceptance criteria. Without a connected visual tool, return a capture/check plan and mark visual verification missing.
