# assets/

Generated binaries. Synced between the two machines with Syncthing, git-ignored.

- `incoming/<job-id>/` - fresh output from workers plus a sidecar `.json` per file
- `approved/` - passed the reviewer; the only folder the Godot project imports from
- `rejected/` - failed review; kept for a while so retries can reference what went wrong
