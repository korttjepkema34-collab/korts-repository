# Studio self-tests

`python -m pytest tests -q` from the repo root (server venv). This is the merge gate for the
studio's own code: the engineer job (docs/23-safety-nets.md) may only merge a fix to `server/`,
`worker/`, `shared/` or `scripts/` if every test here passes and every file compiles.
Add a test for every bug the engineer fixes; that is how the studio stops repeating itself.
