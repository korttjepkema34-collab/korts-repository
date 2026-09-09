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
was actually supplied. The final personal styling, name, avatar and web/mobile preference are open.
