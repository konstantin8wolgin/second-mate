# Approved Direction intake operator guide

Direction intake records exact human-approved product meaning before a packet
is drafted. It does not run Rumble, call a model, approve a route, grant packet
execution, or cause an external effect. Rumble remains a manual or external
conversation, and its raw transcript, scratch reasoning, prompt source,
provider metadata, and credentials remain outside repository authority.

The durable artifact is `.second-mate/directions.json`. It contains immutable,
linear approved versions and portable authority records. It contains no
absolute checkout path. The candidate, approval, and promotion-grant documents
are operator-controlled inputs; only the approved version ledger is project
state.

## Prepare exact text without writing the target

Write the what/why-only Direction Summary outside the target repository. It may
contain context, purpose, outcomes, priorities, capabilities, boundaries,
constraints, success/failure signals, and deferred product decisions. It must
not turn architecture, files, APIs, model routing, tasks, or technical sequence
into product authority.

From the Second Mate environment, prepare D-01:

```sh
second-mate direction prepare \
  --target "$TARGET" \
  --summary "$CONTROL/d01.md" \
  --id D-01 \
  > "$CONTROL/d01-candidate.json"
```

Preparation is read-only. It validates the target as the Git worktree root,
refuses an ignored or missing Git-recorded ledger, preserves the summary bytes
as exact UTF-8 text, binds the candidate to HEAD plus the complete visible
revision fingerprint and packet-run-state digest, and records the current
approved predecessor when one exists. It creates no `.second-mate` directory,
lock, ledger, index update, commit, or provider effect.

Review the candidate's exact text, `candidate_digest`, predecessor, change
note, and `promotion_basis`. A changed repository, Direction ledger, or run
state makes this candidate stale.

## Record Direction approval separately from promotion authority

Second Mate deliberately does not manufacture either human record. Create an
approval document that identifies the exact candidate:

```json
{
  "approved_at": "2026-08-04T11:01:00Z",
  "approved_by": "project-owner",
  "candidate_digest": "<candidate_digest>",
  "decision": "approved",
  "direction_id": "D-01",
  "id": "direction-approval-1",
  "schema_version": 1
}
```

Create a distinct promotion grant. Copy the digest and basis values literally
from the reviewed candidate:

```json
{
  "allowed_effects": ["direction_ledger_write"],
  "allowed_paths": [".second-mate/directions.json"],
  "candidate_digest": "<candidate_digest>",
  "granted_at": "2026-08-04T11:11:00Z",
  "granted_by": "project-owner",
  "id": "direction-promotion-1",
  "run_state_sha256": null,
  "schema_version": 1,
  "stop_conditions": [
    "revision_drift",
    "direction_history_drift",
    "open_run"
  ],
  "target_fingerprint": "<promotion_basis.target_fingerprint>",
  "target_head": "<promotion_basis.target_head>"
}
```

Direction approval confirms the exact what and why. The promotion grant permits
only the one repository-local ledger write. Neither record authorizes packet
implementation, provider use, network or credential access, publication,
deployment, or any other effect.

## Promote and inspect D-01

```sh
second-mate direction promote \
  --target "$TARGET" \
  --candidate "$CONTROL/d01-candidate.json" \
  --approval "$CONTROL/d01-approval.json" \
  --grant "$CONTROL/d01-promotion.json"

second-mate direction show --target "$TARGET" \
  > "$CONTROL/direction.json"
```

Promotion holds the same repository-wide mutation lock as FS-01. It refuses a
missing, broadened, stale, duplicate, or mismatched authority record; revision
or history drift; ignored or missing recorded history; an open packet run; or a
pending close recovery. Initial creation never replaces a late competing
ledger. Later appends use atomic compare-and-exchange and restore a history that
wins a race. Marked partial writes and an interruption after the exact append
exchange are recoverable only by retrying the exact candidate and authority.

`direction show` validates the complete ledger before returning either the
current Direction or a named immutable version:

```sh
second-mate direction show --target "$TARGET" --id D-01
```

The returned JSON is the established Direction schema consumed by `draft`:

```sh
second-mate draft \
  --direction "$CONTROL/direction.json" \
  --packet "$CONTROL/packet.json" \
  > "$CONTROL/draft.json"
```

The ledger is visible project state and must not be ignored. Review it and
include it through the project's separately authorized Git workflow so a fresh
clone can read it. Direction promotion itself does not stage or commit it.

## Append D-02 without changing D-01

A material meaning change creates a new ID and a short change note:

```sh
second-mate direction prepare \
  --target "$TARGET" \
  --summary "$CONTROL/d02.md" \
  --id D-02 \
  --change-note "Add the portable evidence boundary approved by the owner." \
  > "$CONTROL/d02-candidate.json"
```

Review and separately approve/grant D-02 exactly as for D-01, using new
approval and grant IDs. Promotion appends D-02 only when its `supersedes`
record exactly identifies the current D-01 ID and digest. IDs cannot be reused,
unchanged text cannot create a new version, and an old candidate cannot branch
the history after another version wins.

After promotion, `direction show` returns D-02 by default while
`direction show --id D-01` still returns the original approved bytes.

## Recovery and stop rules

- If preparation fails, correct the input or repository state; it made no
  target change.
- If promotion reports revision, history, lock, open-run, or pending-close
  conflict, stop. Do not rewrite the candidate or ledger to bypass the refusal.
- If an exact retry completes a marked partial write, inspect the returned
  version and ledger before continuing.
- If `direction show` rejects malformed, duplicate-field, aliased, missing, or
  non-linear history, preserve the evidence and recover the smallest invalid
  premise. Do not restart at D-01.
- After any new approved ledger version, recreate packet preflight and
  execution consent; prior execution authority is stale by construction.

These behaviors prove only manual approved-Direction intake and safe handoff to
the existing draft flow. They do not prove automated or high-quality Rumble, a
provider run, route or Map execution, pilot usefulness, or complete Direction
coverage.

## Normal-use conversation entry

The intended ordinary entry is now implemented provider-free. A First Mate
conversation can research and clarify scope, prepare one readable exact task,
and turn one explicit user approval into a digest-bound Direction approval plus
a distinct basis-bound one-ledger-write grant. See
[CONVERSATION-HANDOFF.md](CONVERSATION-HANDOFF.md).

The bridge preserves this guide's authority split. Conversation may propose
Direction but cannot infer approval, promote different bytes, or grant route
approval or Execution Consent. Its exact retry is idempotent, and it stops at
`ready-for-preflight` without a provider or task-file mutation. RUN-FACADE-01
must later own preflight, one-shot execution state, evidence, and recovery
behind a high-level boundary without requiring the human to manage digests,
activation JSON, executable modes, or private-state paths. No live run is
authorized or implemented by the conversation bridge.
