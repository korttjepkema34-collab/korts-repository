# Custom interface design

## Implemented desktop shell

Launch `python -m assistant.desktop`. Python/Tkinter provides a locally editable interface with no
web hosting, subscription or UI dependency. Dark slate surfaces, warm gold title, readable task
rows and a split evidence area form the starting visual design.

| Tab | Available now | Next refinement |
|---|---|---|
| Tasks & evidence | Project selector, add goal, status list, persisted details, run/pause/report | Streaming conversation, dependency visualization, diff/image/audio previews |
| Knowledge | Scoped vault search with source paths | Inline note editing, backlinks, history and promotion review |
| Workers & setup | Open active profiles/config/vault/setup | Validated inline forms, per-worker evaluation history |

This is an initial working control shell, not a finished web dashboard. No screenshot of a running
Windows desktop has been verified in this environment. Desktop availability and interaction must
be checked on the actual server; Tkinter import/compilation alone is not a visual test.

## Target flows

1. Select Personal / Business / Game before starting a goal.
2. Discuss scope with cloud brain; show assumptions and acceptance criteria.
3. Show plan and assignments, including dependencies and resource availability.
4. Inspect progress without spending a model request for every refresh.
5. Display actual artifacts and check results next to cloud critique.
6. Offer specific decision/repair choices for blockers.
7. Review the morning report and proposed lessons/skills.

Use truthful status labels: awaiting cloud, awaiting worker, awaiting review, approved draft,
verified candidate, blocked. Never label a draft as a deployed change. Pausing should say it takes
effect after the active step. Show which model/provider performed review and whether vision/audio
was actually supplied. The browser office visual direction is approved below; detailed sprite assets and product naming remain refinements.

## Approved Live Workforce visual direction

The owner approved a detailed pixel-art office: dark navy navigation and panels, warm interior lights, city windows, two connected floors, visible stairs/walkways and distinct characters. The supplied reference is external to this repository; do not claim it is a working UI or reference a missing committed image.

Rooms: Cloud HQ, Server Room, GPU Studio, Creative Studio, World Room, Review Room and Lounge. Atlas, Forge, Pixel, Scout, Scribe and Judge are initial display identities mapped to real specialist IDs. Rooms represent activity; Creative Studio and GPU Studio share one physical GPU. Visual grouping must not merge distinct runtime roles or concurrent instances.

Implement walking, carrying work, handoff, working, waiting, needs-user, error and celebration. Bubbles summarize real events; expressions are UI state. Animations never delay scheduling. The reference's character sheets and theme options are presentation examples, not required permanent panels. Weather, room editing, pets and alternate themes are later scope.

Support a responsive browser view with readable agent details and keyboard selection. On small screens use pan/zoom or scrolling plus an accessible status list. Reduced motion updates position without walking. Pause hidden-tab animation and keep sound off. Details and notifications respect project access boundaries.

Delivery order and verification: [WORKFORCE-PLAN.md](WORKFORCE-PLAN.md) and [LIVE-WORKFORCE-HANDOFF.md](LIVE-WORKFORCE-HANDOFF.md). The existing desktop shell remains available; the browser view is not yet implemented.
