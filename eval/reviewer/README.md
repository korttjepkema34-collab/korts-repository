# Reviewer evaluation set

`manifest.json` lists cases with the expected verdict and the human reason. `scripts/eval_reviewer.py`
runs the orchestrator's exact review path over them and reports accuracy and every miss.

- `--checks-only`: the deterministic layer alone (no model). Baseline on the seeds: 95%, with the
  one miss being palette-coloured text, which only the vision model can catch. That case is there
  on purpose.
- Full mode needs Ollama and `REVIEWER_MODEL`; run it on the server after any change to
  `agents/reviewer.md`, the reviewer prompt in `reviewer.py`, or the model tag. If the number goes
  down, the change was bad, whatever it felt like.

The 20 seed cases are synthetic, cut from the approved mock frames and deliberately broken in one
way each. **Replace them with real assets** as the pipeline produces them: copy the file into
`cases/`, add a manifest entry with `"seed": false` and the reason a human gave. Keep it balanced.
