# Dashboard implementation record — 2026-09-11

## Outcome

The private assistant dashboard now opens on a polished, responsive pixel office called **The
Night Shift**. It uses the authenticated runtime API and recorded SQLite task events. It does not
read game files, call models for decoration, or invent activity.

The supplied office screenshots were used as visual direction. Their newer source artifact was
not present: the available 366,454-byte patch is the earlier 126-test Stage A revision whose own
report says the pixel office was not built. The final implementation therefore builds on the
reviewed runtime and preserves the Windows, OpenRouter audit, and GPU lease corrections made in
this branch.

## Implemented interface

- Persistent desktop sidebar and phone bottom navigation for Office, Tasks, Needs You, Knowledge,
  and System.
- Office is the authenticated landing page. Seven connected rooms show all 17 configured roles.
- Distinct callsigns and named character palettes, city windows, desks, server racks, GPU tower,
  creative props, review board, library/map wall, task counter, truthful state bubbles, and a
  bounded live event feed.
- Worker buttons expose role, model, machine, qualification, current assignment, last activity,
  and event-derived job/review/failure counts. Assigned workers link to the real task conversation.
- Per-project filtering uses server-projected authorized profile scopes. The browser cannot expand
  its session scope.
- Gaming mode changes the GPU room display. Runtime control still goes through the existing
  authenticated, CSRF-protected controller.
- Preview motion is explicitly labeled **SIMULATED PREVIEW**. It changes browser presentation
  only, pauses while the document is hidden, and sends no API mutations.
- Narrow screens keep the two-floor office composition in a contained horizontal scroller. The
  rest of the page has no horizontal overflow.
- Native buttons provide keyboard activation; focus indicators and reduced-motion behavior remain
  available. Dynamic content is inserted as text, never HTML.

## Editable office configuration

`config/assistant/office.json` is copied to the private runtime as `office.json` during initial
setup and included in backups. Callsigns, room assignments, and safe named palettes can be edited
without changing JavaScript. Named palettes intentionally preserve the dashboard's strict Content
Security Policy; arbitrary inline CSS is not accepted.

## Defects found and corrected during verification

1. The initial project filter treated unassigned workers as eligible for every project. The
   sanitized overview now returns the authorized intersection of each profile's project list.
2. The first phone layout stacked all seven rooms vertically. It now retains the two-floor plan and
   pans horizontally inside the office.
3. Inline custom color styles were blocked by `style-src 'self'`. They were replaced with validated
   named palette classes; the policy was not weakened.
4. A custom key handler duplicated native button activation. Removing it restored reliable Enter
   and Space behavior.
5. Closing an SSE browser connection could produce a Windows `ConnectionAbortedError` traceback.
   The server now treats it like the already-handled reset and broken-pipe disconnects.

## Verification evidence

- `node --check assistant/web_static/app.js`: passed.
- `python -m compileall -q assistant scripts tests/assistant`: passed.
- `python -m unittest discover -s tests/assistant -q`: **129 passed**, one Windows symlink-privilege skip.
- `python -m pytest tests -q`: **142 passed**, one Windows symlink-privilege skip and the existing Pillow
  deprecation warning.
- `python scripts/synthetic_e2e.py`: 12/12 passed, including runner refusal, forced interruption,
  resume, repair/review, cancellation, persistence, cloud evidence, pause, and backup restore.
- Browser automation at 1440×960 and 390×844 verified: Office landing, 17 workers, seven rooms,
  Game filter (14 authorized workers), task navigation, keyboard-opened worker panel, desktop
  sidebar, phone bottom navigation, contained office scrolling, zero unnamed buttons, no page-wide
  overflow, zero preview write requests, zero console errors, and zero failed requests.
- Rendered desktop office, worker panel, preview, task, system, inbox, and phone views were opened
  and visually inspected after the automated checks.

## Honest live boundary

This evidence proves the dashboard against a disposable Windows runtime with synthetic records. It
does not prove the server's current systemd/nginx wiring, real long-running inference, or live
Tailscale access. Deployment remains a separate owner review gate. The preview runtime and images
under `work/` are temporary test artifacts and are not part of the public source checkpoint.
