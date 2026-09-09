> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 22 - How it runs: who calls what, when, and how things end

There is exactly one thing that decides work: **the orchestrator loop** on the server
(`server/orchestrator/main.py`), a single Python process that wakes every 20 seconds. Nothing
else acts on its own. The GPU worker waits on a queue. The tools (ComfyUI, the audio API, Godot)
do nothing until called. The nightly pass is a branch of the same loop.

```
every 20 s, on the server                                   on the gaming PC, forever
------------------------------------------------            ----------------------------------
1 reap stale GPU jobs back onto the queue                   wait on Redis for a job of my kinds
2 read results: checks -> vision review -> move files       (image | music | sfx | train)
3 run one text or level job (CPU, in-process)               pop it, load the right tool,
4 run one code job (coder loop, in-process)                 run it, post-process, write files
5 close tasks whose jobs are all finished                   to assets/incoming/ (Syncthing),
6 plan the next backlog task into jobs                      push a result, heartbeat, repeat
7 backlog empty? generate tasks from the design doc
8 once a day: retry a deferred task, playtest, build,
  report, commit, push
9 GPU jobs waiting and the PC silent? wake-on-LAN
```

## One task, end to end

Take task 004, "The Keep: tileset and props".

1. **Plan.** The loop moves `tasks/backlog/004-...md` to `in-progress/` and asks the orchestrator
   model (CPU) for a plan. The model reads the task, the style bible, the world bible and the
   list of approved assets, and answers JSON: a few jobs. For 004 that is several `image` jobs
   (asset_type tile, a subject each) and one `code` job (an importer). The planner fills in the
   mechanics from the asset type: workflow `tileset`, generate at 1024 wide, downscale 8x,
   palette on, transparent off for ground tiles, references `palette.png` and `mock-day.png`,
   the verbatim style suffix on the prompt, four candidates. If the JSON fails validation the
   error goes back to the model once. Each job gets an id and a line in the task file.
2. **Queue.** Image jobs go on the Redis list `jobs:image`. Code, text and level jobs do not go
   to the GPU; the loop runs them itself.
3. **The artist works.** The worker on the gaming PC pops the job. The ComfyUI handler loads
   `worker/workflows/tileset.json`, writes the prompt, negative prompt, size, seed and reference
   image into the titled nodes, posts it to ComfyUI's HTTP API on localhost, waits, downloads
   the PNGs, then post-processes: cut background, downscale with a box filter, snap every pixel
   to the 16 colours, write a normal map. Files land in `assets/incoming/004-<slug>/` with a
   sidecar JSON per image. Syncthing copies them to the server. The worker pushes a result to
   the Redis `results` list and goes back to waiting.
4. **Review.** The loop reads the result. Deterministic checks first: size, off-palette pixels,
   transparency. Survivors go to the vision model one at a time, upscaled so it sees pixels,
   with eight yes/no questions; the verdict is computed from the answers. Approved files move
   to `assets/approved/`, rejected to `assets/rejected/`, the verdict is written into each
   sidecar and into the task file.
5. **Retry.** A rejected job is re-queued with the reviewer's reason in `notes` (the prompt
   gains it), attempt 2, then 3, then it is marked failed.
6. **The coder works.** The code job runs on the server inside the loop: the coder model gets
   the goal, the acceptance list, the approved assets, the conventions, the cookbook, the
   lessons file, and tools (list, read, write, search the engine reference, search docs, headless
   check, tests, screenshot check, proof run, finish). It edits files on a branch, up to 40 tool
   calls, until it calls `finish` or runs out. Then the gate: Godot 3 scan, lint, headless load,
   tests. Green merges to main; red re-queues the job with the error as notes, up to three runs.
   After a merge, if the job named a scene, a proof run replays input and the vision model
   confirms the expected behaviour, else the job reopens.
7. **Close.** When every job of the task is approved, ok or merged, the task moves to `done/`.
   If any is failed, it moves to `deferred/` with the reasons, and the daily pass retries it once
   with the big slow model.
8. **Next.** The loop picks the next backlog task by priority. When the backlog is empty and
   nothing is in progress, it asks the orchestrator model for the next three tasks from the
   design doc, capped per day.

## How each specialist gets told what to do

| Specialist | Told by | The instruction is |
|---|---|---|
| 2D artist (ComfyUI) | an `image` job on the queue | prompt with the style suffix, negative prompt, workflow name, size, seed, references, postprocess block. The role prompt `agents/artist-2d.md` is not sent to ComfyUI; it shapes the planner's job spec |
| Audio (ACE-Step, Stable Audio) | a `music` or `sfx` job on the queue, only when a task's plan includes one (task 016, or the planner deciding a level needs a loop) | prompt, duration, bpm, lyrics or count; the worker calls the audio API wrapper |
| Coder | a `code` job, run in-process | goal, acceptance, scene; plus docs, lessons and tools |
| Writer | a `text` job, run in-process | content type, brief, count; validated for voice and shape |
| Level designer | a `level` job, run in-process | name, size, purpose, required markers; validated for reachability |
| Reviewer | every asset result, automatically | the image, the spec, the style bible, references, the rubric |
| Playtester | the daily pass, automatically | bot screenshots, telemetry, error log |
| Trainer | a `train` job the daily pass queues when enough data exists and `AUTO_TRAIN=1` | recipe and dataset paths |

## How things end

- A **job** ends when it is approved or merged, or when its attempts run out (3 for assets and
  content, 3 coder runs, 40 tool calls per run).
- A **task** ends when all its jobs have ended: done or deferred.
- A **deferred task** is retried once per day with the escalation model; if it fails again it
  stays deferred. That folder is the human's list.
- The **coder** ends a run by calling `finish`, hitting 40 steps, or repeating the same error
  three times.
- The **worker** never ends; it waits. Gaming mode pauses it. The VRAM lock pauses it while the
  coder borrows the GPU.
- The **loop** never ends until the process is stopped. It pauses new work below 20 GB free
  disk and logs every cycle error without dying.

## Timing

| Thing | Cadence |
|---|---|
| Orchestrator cycle | every 20 s; one coder run and one content job per cycle at most |
| GPU worker poll | blocks on the queue, 30 s timeout, heartbeat each loop |
| Stale job reap | after 90 min without completion (training jobs declare longer) |
| Wake-on-LAN | when jobs wait and no heartbeat for 5 min; at most once per 15 min |
| Daily pass | once per 24 h from the last one: deferred retry, playtest, build, report, commit, push |
| Escalation | immediately, when the same failure class repeats 3 times in 24 h |

## The connections

- **Redis** (server): queues per kind, the results list, worker heartbeat and status, the VRAM lock.
- **Syncthing**: `assets/` identical on both machines, so paths in job specs are the same everywhere.
- **Git** (server checkout, Forgejo, GitHub): code on branches merged to main; task board, docs,
  reports committed daily.
- **Files** on the server: `tasks/`, `tasks/.state.json` (every job's status), `reports/`,
  `docs/lessons.md`, `data/traces/`.
- **HTTP on localhost** (gaming PC): the worker to ComfyUI (:8188) and the audio API (:8190).
- **HTTP over Tailscale**: the orchestrator to the gaming PC's Ollama when it borrows the GPU.

## Where a sprite's look actually comes from

The planner only names an asset type and a subject. The look comes from data the planner never
touches: the style bible's suffix and negative prompt (added by the template), the reference
images (palette swatch, the two mock frames, the character sheet once approved) fed through
IP-Adapter, the pixel-art LoRA in the workflow, the post-processor snapping to the palette, the
deterministic checks, and the rubric. Consistency is enforced five times before a human would
have to notice.

## Module map (for the engineer and anyone reading the code)

| File | Responsibility |
|---|---|
| `server/orchestrator/main.py` | the loop: cycle order, results, code/content jobs, task closing, planning, backlog, daily pass, incidents wiring, restart flag |
| `planner.py` | task -> jobs via the orchestrator model; asset-type templates; validation repair; backlog generation |
| `coder.py` | the coder tool loop on a branch; gate (Godot 3 scan, lint, tests); merge; traces |
| `engineer.py` | same loop for the studio's own code; gate is compile + pytest + no test deletion; restart request |
| `writer.py`, `levels.py` | text and level jobs with deterministic validators |
| `reviewer.py`, `checks.py` | vision rubric review; mechanical image checks |
| `vision.py` | windowed screenshots, visual_check, proof runs |
| `playtest.py`, `export.py` | nightly bots + report + bug tasks; nightly Windows build |
| `health.py`, `incidents.py`, `notify.py` | health file, dependency healing, git sanity; incident files; ntfy pushes |
| `llm.py` | clients, model slots, GPU routing, the escalation and vision ladders |
| `docsearch.py`, `rag.py` | engine class-reference search; embedding retrieval over docs and code |
| `state.py`, `gitops.py`, `wake.py`, `report.py`, `traces.py`, `training.py`, `godot.py`, `mcp_bridge.py` | job state; git helpers; wake-on-LAN; daily report; run traces; training jobs; headless Godot runner; optional editor MCP |
| `shared/jobs.py`, `shared/queue.py` | job/result models and kinds; Redis reliable queue |
| `worker/worker.py`, `worker/handlers/*`, `worker/postprocess.py`, `worker/normalmap.py` | GPU worker loop with tool probes and the VRAM lock; ComfyUI, audio, train handlers; palette post-processing; normal maps |
| `game/scripts/*.gd` | Config, Net, Clock, Telemetry autoloads; MapBuilder; dev scripts (screenshot, proof, bot, run_scene) |
| `scripts/*` | doctor, bootstrap, gen_items, eval_reviewer, dump/fetch docs, build index, install gdUnit4 |

