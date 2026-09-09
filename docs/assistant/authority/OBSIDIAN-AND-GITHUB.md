> Owner approved version 0.2 for publication on 2026-09-09. This is governing policy/design, not evidence that runtime controls are implemented. Proposed defaults in the reviewed text are adopted as design defaults; task-specific budgets still require configuration.

# Document 5 — Obsidian Knowledge and GitHub Rules

Status: owner-approved policy design; runtime enforcement remains pending. This section extends the existing MEMORY.md architecture; it does not install plugins, synchronize devices or activate new write permissions.

## K1. Ownership: one authority for each kind of information

| Information | Authoritative location | Other views |
|---|---|---|
| Approved reusable studio rules, code, specialist templates | Reviewed GitHub revision | Versioned read-only reference copies in private vault |
| Private project facts, business specifications, owner notes and accepted lessons | Private vault, with status and revision history | Scoped retrieval supplied to eligible workers |
| Task state, attempts, budgets, mailbox decisions and approval consumption | Server-owned assistant database | Generated Obsidian summaries and future office views |
| Generated candidates and detailed verification evidence | Private runtime artifacts, bound to task/revision | Linked summaries in vault and mailbox |
| Search index | Rebuildable index of eligible notes | Search results; never a second source of facts |

The current GitHub repository is public. Never commit private vault contents, mailbox records, raw business evidence or secrets there. A note's placement in Obsidian does not itself authorize cloud transmission.

## K2. Proposed navigation using existing scope roots

Preserve the existing shared/, business/, game/ and personal/ roots. The General section remains mapped to personal/ until a reviewed migration changes that identifier. New top-level folders must not silently escape the existing index or scope filters.

- shared/studio-home.md: safe common navigation and approved operating references only.
- shared/rules/: pinned copies of approved, nonprivate studio rules.
- shared/specialists/: approved reusable profiles and capabilities.
- business/<project>/home.md: business project overview and links.
- game/<project>/home.md: game overview, canon and evidence links.
- personal/<project>/home.md: general project overview and links.
- Each project: proposed/, knowledge/, decisions/, lessons/, reports/ and mailbox/ views.

An owner-wide dashboard containing private cross-project summaries must stay outside worker-indexed shared/. Provide it through an owner-only view with authenticated access. Do not place all mailbox summaries in shared/ merely to make navigation convenient.

The existing broad project scopes are not proven per-subproject isolation. Until finer isolation is enforced, do not assign a worker access to one subproject and claim that sibling projects are inaccessible.

## K3. Read/write and promotion policy

| Area | Worker behavior proposed |
|---|---|
| Approved rules and specialist authority | Read eligible pinned versions; propose edits separately; no self-promotion |
| Owner-authored notes and business policies | Read within authorized scope; preserve original text; propose corrections |
| Task research and candidate lessons | Write to scoped proposed/ through a controlled writer with provenance |
| Accepted factual/project knowledge | Promote only after independent review and cloud acceptance within approved authority; business-policy and authority changes require Kort |
| Reports and mailbox mirrors | Generated from authoritative records; visibly mark generated content and update time |
| Private credentials | Never store in vault notes or generated reports |

Note fields: stable note ID, project/subproject, kind, status, author/producer, sources, observed date, updated date, evidence/task IDs, reviewer, approved revision where applicable, and supersedes reference. Use statuses proposed, reviewed, approved, superseded, disputed. Reviewed is not automatically approved.

Only an approved rule distributed through the controlled rule mechanism becomes governing instruction. Arbitrary retrieved notes remain evidence, even if their text says “approved.” Enforce promotion and permissions in the controller; Markdown labels alone are not access controls.

Retrieval must distinguish tentative material from established knowledge. Proposed findings can be retrieved for investigation with their status intact; they must not become the default authoritative answer. Superseded notes remain available for history but should not silently override current decisions. If sources conflict, surface that conflict.

## K4. GitHub-to-vault reconciliation

1. Fetch the reviewed source revision into a staging location. Fetching alone does not activate new rules.
2. Compare the new upstream file, the last adopted copy and the local vault copy.
3. If the local file is unchanged, stage the new version. If it was edited locally, preserve both and create a reconciliation item; never overwrite the edit blindly.
4. After appropriate owner approval, activate the rule set atomically and record source commit, content hashes, approval and activation time.
5. Pin each running task to its rule revision. A relevant urgent rule change pauses affected work for replanning; do not silently change its governing context midway through execution.
6. Keep the previous adopted revision available for rollback. Reindex eligible notes after activation and verify stale/deleted content no longer appears as current.

Changes proposed from Obsidian follow the reverse review path: preserve a proposed copy, sanitize reusable content, prepare a GitHub diff, obtain owner publication approval, then adopt the approved revision. Editing a vault copy cannot directly rewrite GitHub or authorize a push.

## K5. Mailbox and report projections

The database owns item ID, status, response and action authorization. An Obsidian mailbox note is a readable projection containing last-updated time, task/revision links, question and evidence. The office will display the same item ID later.

Editing generated text, checking a Markdown checkbox, reading a note, or deleting a projection does not approve, resolve or delete its underlying task. Initially use an authenticated controller command/interface for responses. A future Obsidian response adapter must validate identity, revision, explicit action, conflicts and replay protection before it can change state.

Generated summaries can be rebuilt. Distinguish stale data from an empty mailbox. Reports include factual actions, outcomes, evidence, reviewer conclusions and uncertainty; they do not expose hidden model reasoning. Broken or unavailable evidence links are shown as unavailable, not as verification success.

## K6. Worked navigation example — admin calculation repair

Business project home links to the overnight report. The report links to the issue, approved calculation specification, candidate revision, independent expected examples, test results and review. If expected behavior is unknown, its mailbox item links to the disputed assumption and asks Kort for the authoritative rule. Unrelated layout work can proceed in its own candidate. Kort's answer is recorded through the controller, then the task is replanned and checked against that answer.

This example is a design fixture, not a claim that the tax issue has been investigated or fixed.

## K7. Compatibility and implementation boundary

| Capability | Current evidence / remaining work |
|---|---|
| Markdown vault and broad scope roots | Existing assistant design and code |
| SQLite full-text indexing and scope-filtered search | Existing core.py implementation; not semantic retrieval |
| Memory MCP | Existing read-only interactive adapter; session configuration and live discovery still required |
| Vault initialization | Existing setup behavior; not ongoing bidirectional sync |
| Metadata-aware knowledge promotion | Proposed; do not assume current indexing enforces approval status |
| Per-subproject access boundaries | Pending implementation and tests |
| Owner dashboard, report and mailbox projections | Proposed; persistent mailbox controller also remains to be built |
| Three-way rule reconciliation and task revision pinning | Proposed enforcement work |
| Windows, Obsidian and provider operation on actual PCs | Live qualification outstanding |

No additional AI plugin is required by this architecture. Plugins may be evaluated later for a concrete missing capability. Mobile vault access and synchronization remain a setup decision; the Safari office link does not synchronize Obsidian. Keep active SQLite/WAL files server-owned and out of live multi-device sync. Back up private notes and runtime state separately from public source, and verify a restore before relying on unattended work.

## K8. Acceptance scenarios for implementation

- Business private content never appears in game retrieval or shared dashboards.
- A worker restricted to one subproject cannot query sibling project notes once that capability is enabled.
- Proposed and superseded calculations cannot silently displace an approved specification.
- A GitHub update preserves a locally edited rule and opens a conflict instead of overwriting it.
- Editing or deleting a mailbox mirror does not grant approval or lose authoritative decisions.
- Repeated delivery of the same owner response does not duplicate the action.
- Notes removed or changed are correctly reflected after reindexing.
- Restart rebuilds projections without losing task IDs, rule revisions or pending decisions.
- Broken artifact links and stale reports are reported honestly.
- Restore reproduces a known note, task and evidence reference from backup.

These are future behavioral tests. Draft validation consisted of comparing the ownership and scope proposal against MEMORY.md and inspecting core.py indexing/search locations. No runtime change or live integration is claimed.

## Proposed next implementation order after document approval

1. Publish the approved authority documents and reconcile legacy contradictory instructions.
2. Implement knowledge status/provenance handling and controlled rule adoption with scope tests.
3. Implement persistent mailbox decisions and readable project reports against the existing task authority.
4. Add owner navigation and Obsidian projections; verify actual Windows/vault use and backup restore.
5. Connect the deferred office to these same records when office work resumes.

The owner approved the version 0.2 package for publication. This ownership map governs implementation; unimplemented controls must not be reported as active.
