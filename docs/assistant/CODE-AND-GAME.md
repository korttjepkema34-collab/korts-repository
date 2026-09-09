# Code, business projects and Godot

## Code workspace lifecycle

A code-sandbox worker receives the goal, cloud acceptance criteria, retrieved project notes and the
exact configured source files. It returns complete file replacements as JSON. The controller:

1. Clones committed source into the private runtime and selects its exact source HEAD.
2. Removes the remote. The original checkout is not changed.
3. Validates write paths against allowed prefixes, extensions and traversal checks.
4. Applies up to 12 file replacements, records the staged diff, then runs configured commands.
5. Sends the diff and actual exit/output records to the cloud reviewer.
6. Requests repair if checks fail or review does not explicitly pass every criterion.
7. Retains the candidate for inspection; it never automatically merges or deploys.

A clone is not an operating-system sandbox. Check commands run code; use a dedicated execution
account or VM with intended access only. Configure dependencies in the candidate environment.
Secrets and production credentials are not copied by the controller, but anything already committed
to the source repository is part of its clone: correct that before enabling execution.

Allowed extensions and prefixes are deliberately narrow. Deletions, dependency installation,
unrestricted shell tools and automatic integration are not implemented in this adapter. A task
requiring them must be handled explicitly instead of being labeled complete. Configure context
files for each actual task; this first adapter does not autonomously browse the entire repository.

## Godot

Existing files target Godot 4 and use GDScript. Keep Reaper's Relics design, world, style, items and
scope ladder. Do not replace them with a newly invented game. The historical scripts name a 4.3
binary; choose and record a tested Godot 4 version before installing add-ons or changing APIs.

1. Download the selected Windows Godot build and matching export templates from
   [Godot](https://godotengine.org/download/windows/).
2. Open `game/project.godot` once. Record import/parse errors rather than assuming the skeleton works.
3. Run the engine's headless import/load command and the project's actual test runner.
4. Inspect `scripts/install_gdunit4.ps1`; choose a gdUnit4 version compatible with the pinned engine,
   install it, and confirm test discovery. A missing test runner is not a pass.
5. Open `game/scenes/main/main.tscn` visibly and verify input, drawing, logs and screenshots.
6. For this multiplayer design, verify dedicated server and two clients/bots separately. Existing
   `game/scripts/dev/` helpers and legacy playtest code are references to qualify, not proven results.
7. Produce a Windows build with matching templates and run that exported build.

Example private code config (replace the executable path with your real pinned binary):

```json
{
  "execution_enabled": true,
  "source": "C:/studio",
  "allowed_prefixes": ["game/"],
  "context_files": ["game/scenes/main/main.gd"],
  "checks": [
    ["C:/Godot/Godot.exe", "--headless", "--path", "{workspace}/game", "--editor", "--quit"]
  ],
  "check_timeout_seconds": 300
}
```

This example is an import gate only. Add an actual test command before approving logic changes.
Some engines emit errors while exiting zero; inspect output and use a wrapper that fails on script
errors where required. The legacy `server/orchestrator/godot.py` already contains relevant checks;
review and qualify it before use. Zero exit status alone is not proof of game behavior.

## Business

The public personal repository is not the private Mountain Men Services source or customer store.
Clone the intended business repository separately with the correct access; configure its local
path in `code_projects.business.source`. Keep its existing AGENTS instructions and deployment rules.

Configure a small relevant context set and actual project checks, such as lint/typecheck/tests/build
using installed dependencies in the isolated clone. Do not invent commands without checking the
business repository. UI changes require browser screenshots and user-flow checks; backend work
requires business-rule examples and data/integration tests. No customer writes or production
publishing are enabled by the draft/code-candidate controller.

## Integration after review

Inspect the candidate diff and evidence, rerun checks against the latest target revision, resolve
conflicts explicitly, then create a branch/PR in the target repository. Review approval is tied to
the submitted artifact; changing it requires re-review. Automatic cross-project PR creation and
combined integration testing are remaining work, tracked in ACCEPTANCE.md.

Source: [Godot CLI](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html).
